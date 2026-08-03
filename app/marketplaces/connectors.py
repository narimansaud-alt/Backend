import json
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date
from typing import Any

import httpx

from app.marketplaces.metrics import SYNC_API_ERRORS
from app.marketplaces.models import Marketplace, SyncKind


@dataclass(frozen=True)
class ConnectorPage:
    records: list[dict[str, Any]]
    next_cursor: dict[str, Any] | None


@dataclass(frozen=True)
class CredentialValidation:
    scopes: frozenset[str]


class MarketplaceAPIError(RuntimeError):
    def __init__(
        self,
        *,
        code: str,
        status_code: int | None,
        safe_message: str,
        retry_after: float | None = None,
    ) -> None:
        super().__init__(safe_message)
        self.code = code
        self.status_code = status_code
        self.safe_message = safe_message
        self.retry_after = retry_after


class MarketplaceConnectorInterface(ABC):
    marketplace: Marketplace
    supported_kinds: frozenset[SyncKind]

    @abstractmethod
    async def validate_credentials(self, credential: str, external_id: str) -> CredentialValidation: ...

    @abstractmethod
    async def fetch_page(
        self,
        *,
        kind: SyncKind,
        credential: str,
        external_id: str,
        date_from: date,
        date_to: date,
        cursor: dict[str, Any] | None,
    ) -> ConnectorPage: ...


@dataclass
class BaseHTTPConnector(MarketplaceConnectorInterface):
    client: httpx.AsyncClient

    async def _request(
        self,
        method: str,
        url: str,
        *,
        headers: dict[str, str],
        params: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
    ) -> Any:
        try:
            response = await self.client.request(method, url, headers=headers, params=params, json=json_body)
        except (httpx.TimeoutException, httpx.NetworkError) as exc:
            raise MarketplaceAPIError(
                code="MARKETPLACE_UNAVAILABLE",
                status_code=None,
                safe_message="Marketplace request failed",
            ) from exc
        if response.status_code >= 400:
            SYNC_API_ERRORS.labels(self.marketplace.value, str(response.status_code)).inc()
            retry_after_header = response.headers.get("Retry-After")
            retry_after = None
            if retry_after_header:
                try:
                    retry_after = float(retry_after_header)
                except ValueError:
                    retry_after = None
            code = {
                401: "TOKEN_INVALID",
                403: "TOKEN_SCOPE_MISSING",
                420: "RATE_LIMITED",
                429: "RATE_LIMITED",
            }.get(
                response.status_code, "MARKETPLACE_UNAVAILABLE" if response.status_code >= 500 else "REQUEST_REJECTED"
            )
            raise MarketplaceAPIError(
                code=code,
                status_code=response.status_code,
                safe_message=f"Marketplace returned HTTP {response.status_code}",
                retry_after=retry_after,
            )
        try:
            return response.json()
        except ValueError as exc:
            raise MarketplaceAPIError(
                code="MARKETPLACE_UNAVAILABLE",
                status_code=response.status_code,
                safe_message="Marketplace returned an invalid response",
            ) from exc


class WildberriesConnector(BaseHTTPConnector):
    marketplace = Marketplace.WILDBERRIES
    supported_kinds = frozenset(
        {
            SyncKind.ORDERS,
            SyncKind.SALES_RETURNS,
            SyncKind.FINANCE_TRANSACTIONS,
        }
    )

    @staticmethod
    def _headers(credential: str) -> dict[str, str]:
        return {"Authorization": credential}

    async def validate_credentials(self, credential: str, external_id: str) -> CredentialValidation:
        probes = {
            "statistics": "https://statistics-api.wildberries.ru/ping",
            "analytics": "https://seller-analytics-api.wildberries.ru/ping",
        }
        scopes: set[str] = set()
        for scope, url in probes.items():
            try:
                await self._request("GET", url, headers=self._headers(credential))
            except MarketplaceAPIError as exc:
                if exc.status_code in {401, 403}:
                    continue
                raise
            scopes.add(scope)
        if not scopes:
            raise MarketplaceAPIError(
                code="TOKEN_INVALID", status_code=401, safe_message="Wildberries token was rejected"
            )
        return CredentialValidation(frozenset(scopes))

    async def fetch_page(
        self,
        *,
        kind: SyncKind,
        credential: str,
        external_id: str,
        date_from: date,
        date_to: date,
        cursor: dict[str, Any] | None,
    ) -> ConnectorPage:
        if kind not in self.supported_kinds:
            raise ValueError(f"Unsupported Wildberries sync kind: {kind}")
        headers = self._headers(credential)
        if kind in {SyncKind.ORDERS, SyncKind.SALES_RETURNS}:
            resource = "orders" if kind is SyncKind.ORDERS else "sales"
            date_cursor = (cursor or {}).get("last_change_date", date_from.isoformat())
            data = await self._request(
                "GET",
                f"https://statistics-api.wildberries.ru/api/v1/supplier/{resource}",
                headers=headers,
                params={"dateFrom": date_cursor, "flag": 0},
            )
            if not isinstance(data, list):
                raise MarketplaceAPIError(
                    code="MARKETPLACE_UNAVAILABLE", status_code=200, safe_message="Unexpected Wildberries response"
                )
            next_cursor = None
            if len(data) >= 80_000:
                next_cursor = {"last_change_date": data[-1]["lastChangeDate"]}
            return ConnectorPage(records=data, next_cursor=next_cursor)
        if kind is SyncKind.FINANCE_TRANSACTIONS:
            rrd_id = int((cursor or {}).get("rrdid", 0))
            data = await self._request(
                "GET",
                "https://statistics-api.wildberries.ru/api/v5/supplier/reportDetailByPeriod",
                headers=headers,
                params={"dateFrom": date_from.isoformat(), "dateTo": date_to.isoformat(), "rrdid": rrd_id},
            )
            if not isinstance(data, list):
                raise MarketplaceAPIError(
                    code="MARKETPLACE_UNAVAILABLE", status_code=200, safe_message="Unexpected Wildberries response"
                )
            next_cursor = {"rrdid": data[-1]["rrd_id"]} if len(data) >= 100_000 else None
            return ConnectorPage(records=data, next_cursor=next_cursor)
        if kind is SyncKind.STOCKS:
            data = await self._request(
                "POST",
                "https://seller-analytics-api.wildberries.ru/api/analytics/v1/stocks-report/wb-warehouses",
                headers=headers,
                json_body={"currentPeriod": {"start": date_from.isoformat(), "end": date_to.isoformat()}},
            )
            records = data.get("data", {}).get("items", data.get("data", [])) if isinstance(data, dict) else []
            return ConnectorPage(records=list(records), next_cursor=None)
        data = await self._request(
            "POST",
            "https://seller-analytics-api.wildberries.ru/api/analytics/v3/sales-funnel/products/history",
            headers=headers,
            json_body={
                "period": {"start": date_from.isoformat(), "end": date_to.isoformat()},
                "nmIds": [],
                "brandNames": [],
                "subjectIds": [],
                "tagIds": [],
                "timezone": "Europe/Moscow",
                "aggregationLevel": "day",
            },
        )
        records = data.get("data", {}).get("products", []) if isinstance(data, dict) else []
        return ConnectorPage(records=list(records), next_cursor=None)


class OzonConnector(BaseHTTPConnector):
    marketplace = Marketplace.OZON
    supported_kinds = frozenset({SyncKind.ORDERS, SyncKind.FINANCE_TRANSACTIONS})

    @staticmethod
    def _headers(credential: str) -> dict[str, str]:
        try:
            parsed = json.loads(credential)
            client_id, api_key = parsed["client_id"], parsed["api_key"]
        except (json.JSONDecodeError, KeyError, TypeError) as exc:
            raise MarketplaceAPIError(
                code="TOKEN_INVALID",
                status_code=401,
                safe_message="Ozon credential must contain client_id and api_key",
            ) from exc
        return {"Client-Id": str(client_id), "Api-Key": str(api_key), "Content-Type": "application/json"}

    async def validate_credentials(self, credential: str, external_id: str) -> CredentialValidation:
        await self._request(
            "POST",
            "https://api-seller.ozon.ru/v3/product/list",
            headers=self._headers(credential),
            json_body={"filter": {}, "last_id": "", "limit": 1},
        )
        return CredentialValidation(self.supported_kinds_to_scopes())

    def supported_kinds_to_scopes(self) -> frozenset[str]:
        return frozenset(kind.value for kind in self.supported_kinds)

    async def fetch_page(
        self,
        *,
        kind: SyncKind,
        credential: str,
        external_id: str,
        date_from: date,
        date_to: date,
        cursor: dict[str, Any] | None,
    ) -> ConnectorPage:
        if kind not in self.supported_kinds:
            raise ValueError(f"Unsupported Ozon sync kind: {kind}")
        headers = self._headers(credential)
        if kind is SyncKind.ORDERS:
            offset = int((cursor or {}).get("offset", 0))
            body = {
                "dir": "ASC",
                "limit": 1000,
                "offset": offset,
                "filter": {"since": f"{date_from.isoformat()}T00:00:00Z", "to": f"{date_to.isoformat()}T23:59:59Z"},
                "with": {"analytics_data": True, "financial_data": True},
            }
            data = await self._request(
                "POST", "https://api-seller.ozon.ru/v3/posting/fbs/list", headers=headers, json_body=body
            )
            records = data.get("result", {}).get("postings", [])
            has_next = bool(data.get("result", {}).get("has_next"))
            return ConnectorPage(
                records=list(records), next_cursor={"offset": offset + len(records)} if has_next else None
            )
        if kind is SyncKind.FINANCE_TRANSACTIONS:
            page = int((cursor or {}).get("page", 1))
            body = {
                "filter": {
                    "date": {"from": f"{date_from.isoformat()}T00:00:00Z", "to": f"{date_to.isoformat()}T23:59:59Z"},
                    "transaction_type": "all",
                },
                "page": page,
                "page_size": 1000,
            }
            data = await self._request(
                "POST", "https://api-seller.ozon.ru/v3/finance/transaction/list", headers=headers, json_body=body
            )
            result = data.get("result", {})
            records = result.get("operations", [])
            next_cursor = {"page": page + 1} if page < int(result.get("page_count", page)) else None
            return ConnectorPage(records=list(records), next_cursor=next_cursor)
        offset = int((cursor or {}).get("offset", 0))
        data = await self._request(
            "POST",
            "https://api-seller.ozon.ru/v2/analytics/stock_on_warehouses",
            headers=headers,
            json_body={"limit": 1000, "offset": offset},
        )
        records = data.get("result", {}).get("rows", data.get("result", []))
        next_cursor = {"offset": offset + len(records)} if len(records) == 1000 else None
        return ConnectorPage(records=list(records), next_cursor=next_cursor)


class YandexMarketConnector(BaseHTTPConnector):
    marketplace = Marketplace.YANDEX_MARKET
    supported_kinds = frozenset({SyncKind.ORDERS})

    @staticmethod
    def _headers(credential: str) -> dict[str, str]:
        return {"Api-Key": credential}

    async def validate_credentials(self, credential: str, external_id: str) -> CredentialValidation:
        await self._request(
            "GET",
            "https://api.partner.market.yandex.ru/v2/campaigns",
            headers=self._headers(credential),
        )
        return CredentialValidation(frozenset({"inventory-and-order-processing:read-only"}))

    async def fetch_page(
        self,
        *,
        kind: SyncKind,
        credential: str,
        external_id: str,
        date_from: date,
        date_to: date,
        cursor: dict[str, Any] | None,
    ) -> ConnectorPage:
        if kind is not SyncKind.ORDERS:
            raise ValueError(f"Unsupported Yandex Market sync kind: {kind}")
        token = (cursor or {}).get("page_token")
        body: dict[str, Any] = {
            "dateFrom": date_from.isoformat(),
            "dateTo": date_to.isoformat(),
            "limit": 200,
        }
        if token:
            body["pageToken"] = token
        data = await self._request(
            "POST",
            f"https://api.partner.market.yandex.ru/v1/businesses/{external_id}/orders",
            headers=self._headers(credential),
            json_body=body,
        )
        result = data.get("result", {})
        records = result.get("orders", [])
        next_token = result.get("paging", {}).get("nextPageToken")
        return ConnectorPage(records=list(records), next_cursor={"page_token": next_token} if next_token else None)


@dataclass(frozen=True)
class ConnectorFactory:
    connectors: dict[Marketplace, MarketplaceConnectorInterface]

    def get(self, marketplace: Marketplace | str) -> MarketplaceConnectorInterface:
        marketplace_value = Marketplace(marketplace)
        return self.connectors[marketplace_value]
