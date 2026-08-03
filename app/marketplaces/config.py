from app.core.configs.base import BaseConfig


class MarketplaceConfig(BaseConfig):
    CREDENTIAL_ENCRYPTION_KEYS: dict[int, str] = {}
    CREDENTIAL_ACTIVE_KEY_VERSION: int = 1
    MARKETPLACE_HTTP_TIMEOUT_SECONDS: float = 30
    MARKETPLACE_MAX_RETRIES: int = 5


marketplace_config = MarketplaceConfig()
