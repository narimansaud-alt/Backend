import base64
from datetime import date
from decimal import Decimal
from io import BytesIO
from zipfile import ZipFile

import pytest

from app.analytics.custom_metrics import InvalidMetricExpression, MetricExpression
from app.analytics.exports import _csv_bytes, _xlsx_bytes
from app.analytics.formulas import MetricInputs, calculate_metrics, safe_ratio
from app.analytics.sanitizer import sanitize_client_error
from app.marketplaces.credentials import CredentialCipher, CredentialDecryptionError
from app.marketplaces.models import Marketplace, SyncKind
from app.marketplaces.normalizers import normalize_record
from app.marketplaces.retry import RetryAction, retry_decision, split_period
from app.organizations.models import OrganizationRole
from app.organizations.policies import OrganizationScope, permissions_for_role


def test_management_formulas_and_zero_denominators() -> None:
    values = MetricInputs(
        orders_qty=Decimal("10"),
        sales_amount=Decimal("1000"),
        sales_qty=Decimal("8"),
        returns_amount=Decimal("100"),
        marketplace_commission=Decimal("90"),
        logistics=Decimal("40"),
        cogs=Decimal("300"),
        advertising_cost=Decimal("50"),
        operating_expenses=Decimal("20"),
        tax=Decimal("30"),
    )
    metrics = calculate_metrics(values)
    assert metrics["net_sales"] == Decimal("900")
    assert metrics["buyout_rate"] == Decimal("80")
    assert metrics["gross_profit"] == Decimal("470")
    assert metrics["operating_profit"] == Decimal("400")
    assert metrics["net_profit"] == Decimal("370")
    assert safe_ratio(Decimal("1"), Decimal("0")) is None


def test_metric_dsl_accepts_only_known_arithmetic() -> None:
    expression = MetricExpression.parse(
        "(net_sales - advertising_cost) / cogs",
        {"net_sales", "advertising_cost", "cogs"},
    )
    assert expression.evaluate(
        {
            "net_sales": Decimal("100"),
            "advertising_cost": Decimal("10"),
            "cogs": Decimal("30"),
        }
    ) == Decimal("3")
    assert expression.to_dict()["type"] == "Expression"
    assert (
        MetricExpression.parse("net_sales / cogs", {"net_sales", "cogs"}).evaluate(
            {"net_sales": Decimal("1"), "cogs": Decimal("0")}
        )
        is None
    )
    with pytest.raises(InvalidMetricExpression):
        MetricExpression.parse("__import__('os').system('whoami')", {"net_sales"})


def test_credentials_are_authenticated_and_bound_to_cabinet() -> None:
    key = base64.urlsafe_b64encode(bytes(range(32))).decode()
    cipher = CredentialCipher({2: key}, active_key_version=2)
    encrypted = cipher.encrypt("top-secret-token", cabinet_id="cabinet-a")
    assert b"top-secret-token" not in encrypted.value
    assert encrypted.masked_hint == "to…oken"
    assert cipher.decrypt(encrypted.value, key_version=2, cabinet_id="cabinet-a") == "top-secret-token"
    with pytest.raises(CredentialDecryptionError):
        cipher.decrypt(encrypted.value, key_version=2, cabinet_id="cabinet-b")


def test_retry_policy_and_period_windows() -> None:
    assert retry_decision(status_code=401, attempt=1, max_attempts=5).action is RetryAction.PAUSE
    assert retry_decision(status_code=400, attempt=1, max_attempts=5).action is RetryAction.FAIL
    assert retry_decision(status_code=429, attempt=1, max_attempts=5).action is RetryAction.RETRY
    assert split_period(date(2026, 1, 1), date(2026, 3, 5), 30) == [
        (date(2026, 1, 1), date(2026, 1, 30)),
        (date(2026, 1, 31), date(2026, 3, 1)),
        (date(2026, 3, 2), date(2026, 3, 5)),
    ]


def test_marketplace_normalization_has_stable_keys() -> None:
    wb = normalize_record(
        Marketplace.WILDBERRIES,
        SyncKind.ORDERS,
        {
            "srid": "wb-order-1",
            "date": "2026-08-01T10:00:00",
            "priceWithDisc": 1250,
            "nmId": 42,
            "lastChangeDate": "2026-08-01T10:01:00+03:00",
        },
    )
    assert wb[0].external_key == "wb-order-1"
    assert wb[0].amount == Decimal("1250")

    ozon = normalize_record(
        Marketplace.OZON,
        SyncKind.ORDERS,
        {
            "posting_number": "oz-1",
            "in_process_at": "2026-08-01T10:00:00Z",
            "products": [{"offer_id": "sku", "quantity": 2, "price": "99.50"}],
        },
    )
    assert ozon[0].external_key == "oz-1:sku"
    assert ozon[0].amount == Decimal("199.00")

    yandex = normalize_record(
        Marketplace.YANDEX_MARKET,
        SyncKind.ORDERS,
        {
            "id": 10,
            "creationDate": "2026-08-01",
            "statusUpdateDate": "2026-08-01T10:00:00Z",
            "items": [{"shopSku": "sku", "count": 2, "prices": [{"value": 50}]}],
        },
    )
    assert yandex[0].external_key == "10:sku"
    assert yandex[0].amount == Decimal("100")


def test_role_matrix_and_cabinet_intersection() -> None:
    assert "organization:manage" in permissions_for_role(OrganizationRole.OWNER)
    assert "organization:manage" not in permissions_for_role(OrganizationRole.MANAGER)
    from uuid import UUID

    one = UUID("00000000-0000-0000-0000-000000000001")
    two = UUID("00000000-0000-0000-0000-000000000002")
    scope = OrganizationScope(
        organization_id=one,
        role=OrganizationRole.VIEWER,
        permissions=permissions_for_role(OrganizationRole.VIEWER),
        cabinet_ids=frozenset({one}),
    )
    assert scope.restrict_cabinets({one, two}) == frozenset({one})


def test_client_error_sanitization_removes_tokens_and_email() -> None:
    safe = sanitize_client_error(
        route="/orders",
        release="1.0",
        browser="test",
        message="Authorization: Bearer abc.def and user@example.com",
        stack="api_key=very-secret-value",
        component_stack=None,
        request_id="request-1",
    )
    assert "abc.def" not in safe.message
    assert "user@example.com" not in safe.message
    assert "very-secret-value" not in (safe.stack or "")


def test_export_serializers_create_safe_csv_and_valid_xlsx_package() -> None:
    headers = ["sku", "revenue"]
    rows = [['=HYPERLINK("https://example.invalid")', "125.50"]]

    csv_data = _csv_bytes(headers, rows).decode("utf-8-sig")
    assert "'=HYPERLINK" in csv_data

    with ZipFile(BytesIO(_xlsx_bytes(headers, rows))) as archive:
        assert "xl/workbook.xml" in archive.namelist()
        sheet = archive.read("xl/worksheets/sheet1.xml")
        assert b"HYPERLINK" in sheet
