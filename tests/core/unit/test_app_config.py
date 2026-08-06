import pytest
from pydantic import ValidationError

from app.core.configs.app import AppConfig


def test_production_config_requires_critical_settings() -> None:
    with pytest.raises(ValidationError, match="Missing required production settings"):
        AppConfig(ENVIRONMENT="production")


def test_production_config_requires_initial_admin_and_rejects_default_password() -> None:
    required = {
        "SECRET_KEY": "secret",
        "JWT_SECRET_KEY": "jwt-secret",
        "POSTGRES_SERVER": "db",
        "POSTGRES_USER": "user",
        "POSTGRES_PASSWORD": "database-password",
        "POSTGRES_DB": "app",
        "REDIS_HOST": "redis",
        "BROKER_URL": "kafka:9092",
    }
    with pytest.raises(ValidationError, match="INITIAL_ADMIN_EMAIL"):
        AppConfig(ENVIRONMENT="production", **required)
    with pytest.raises(ValidationError, match="must be changed"):
        AppConfig(
            ENVIRONMENT="production",
            INITIAL_ADMIN_EMAIL="admin@example.com",
            INITIAL_ADMIN_USERNAME="admin",
            INITIAL_ADMIN_PASSWORD="ChangeMe123!",
            **required,
        )
