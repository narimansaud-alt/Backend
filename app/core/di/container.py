from dishka import AsyncContainer, Provider, make_async_container

from app.analytics.providers import AnalyticsProvider
from app.auth.providers import AuthModuleProvider
from app.catalog.providers import CatalogProvider
from app.core.di import get_core_providers
from app.finance.providers import FinanceProvider
from app.marketplaces.providers import MarketplacesProvider
from app.organizations.providers import OrganizationsProvider


def create_container(*app_providers: Provider) -> AsyncContainer:
    providers = [
        # Core providers
        *get_core_providers(),
        # Module providers
        AuthModuleProvider(),
        OrganizationsProvider(),
        MarketplacesProvider(),
        AnalyticsProvider(),
        CatalogProvider(),
        FinanceProvider(),
    ]

    return make_async_container(*providers, *app_providers)
