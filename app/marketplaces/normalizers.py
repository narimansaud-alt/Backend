from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from app.marketplaces.models import Marketplace, SyncKind


@dataclass(frozen=True)
class CanonicalRecord:
    external_key: str
    business_date: date
    quantity: Decimal
    amount: Decimal
    operation_type: str | None = None
    external_offer_id: str | None = None
    source_updated_at: datetime | None = None


def _date(value: str) -> date:
    return date.fromisoformat(value[:10])


def _datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def normalize_record(
    marketplace: Marketplace,
    kind: SyncKind,
    record: dict[str, Any],
) -> list[CanonicalRecord]:
    if marketplace is Marketplace.WILDBERRIES:
        if kind is SyncKind.ORDERS:
            return [
                CanonicalRecord(
                    external_key=str(record["srid"]),
                    business_date=_date(record["date"]),
                    quantity=Decimal("1"),
                    amount=Decimal(str(record.get("priceWithDisc", record.get("finishedPrice", 0)))),
                    external_offer_id=str(record.get("nmId", "")),
                    source_updated_at=_datetime(record.get("lastChangeDate")),
                )
            ]
        if kind is SyncKind.SALES_RETURNS:
            sale_id = str(record.get("saleID", record.get("srid", "")))
            operation = (
                "return" if sale_id.upper().startswith("R") or Decimal(str(record.get("forPay", 0))) < 0 else "sale"
            )
            return [
                CanonicalRecord(
                    external_key=sale_id,
                    business_date=_date(record["date"]),
                    quantity=Decimal("1"),
                    amount=abs(Decimal(str(record.get("priceWithDisc", record.get("forPay", 0))))),
                    operation_type=operation,
                    external_offer_id=str(record.get("nmId", "")),
                    source_updated_at=_datetime(record.get("lastChangeDate")),
                )
            ]
        if kind is SyncKind.FINANCE_TRANSACTIONS:
            finance_date = record.get("sale_dt", record.get("rr_dt"))
            if not isinstance(finance_date, str):
                raise ValueError("Wildberries finance row has no business date")
            return [
                CanonicalRecord(
                    external_key=str(record["rrd_id"]),
                    business_date=_date(finance_date),
                    quantity=Decimal(str(record.get("quantity", 1))),
                    amount=Decimal(str(record.get("ppvz_for_pay", 0))),
                    operation_type=str(record.get("supplier_oper_name", "other")),
                    external_offer_id=str(record.get("nm_id", "")),
                    source_updated_at=_datetime(record.get("rr_dt")),
                )
            ]
    if marketplace is Marketplace.OZON:
        if kind is SyncKind.ORDERS:
            result: list[CanonicalRecord] = []
            for product in record.get("products", []):
                result.append(
                    CanonicalRecord(
                        external_key=f"{record['posting_number']}:{product.get('sku', product.get('offer_id'))}",
                        business_date=_date(record["in_process_at"]),
                        quantity=Decimal(str(product.get("quantity", 1))),
                        amount=Decimal(str(product.get("price", 0))) * Decimal(str(product.get("quantity", 1))),
                        external_offer_id=str(product.get("offer_id", product.get("sku", ""))),
                        source_updated_at=_datetime(record.get("in_process_at")),
                    )
                )
            return result
        if kind is SyncKind.FINANCE_TRANSACTIONS:
            return [
                CanonicalRecord(
                    external_key=str(record["operation_id"]),
                    business_date=_date(record["operation_date"]),
                    quantity=Decimal("1"),
                    amount=Decimal(str(record.get("amount", 0))),
                    operation_type=str(record.get("operation_type", "other")),
                    source_updated_at=_datetime(record.get("operation_date")),
                )
            ]
    if marketplace is Marketplace.YANDEX_MARKET and kind is SyncKind.ORDERS:
        result = []
        for item in record.get("items", []):
            key = f"{record['id']}:{item.get('shopSku', item.get('marketSku'))}"
            prices = item.get("prices") or []
            unit_price = sum(Decimal(str(price.get("value", 0))) for price in prices)
            quantity = Decimal(str(item.get("count", 1)))
            result.append(
                CanonicalRecord(
                    external_key=key,
                    business_date=_date(record["creationDate"]),
                    quantity=quantity,
                    amount=unit_price * quantity,
                    external_offer_id=str(item.get("shopSku", item.get("marketSku", ""))),
                    source_updated_at=_datetime(record.get("statusUpdateDate")),
                )
            )
        return result
    return []
