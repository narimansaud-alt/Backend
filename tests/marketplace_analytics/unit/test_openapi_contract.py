from app.main import init_app


def test_marketplace_analytics_openapi_contract() -> None:
    schema = init_app().openapi()
    required = {
        "/ready",
        "/api/v1/organizations",
        "/api/v1/cabinets",
        "/api/v1/analytics/overview",
        "/api/v1/analytics/timeseries",
        "/api/v1/finance/profit-loss",
        "/api/v1/finance/cash-flow",
        "/api/v1/finance/transactions",
        "/api/v1/observability/client-errors",
        "/api/v1/exports",
        "/api/v1/exports/{export_id}",
    }
    assert required <= set(schema["paths"])
    assert "/api/v1/users/register" not in schema["paths"]
    assert "AnalyticsOverviewResponse" in schema["components"]["schemas"]
