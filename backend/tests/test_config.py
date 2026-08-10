from app.config.environment import (
    Environment,
    get_environment,
    validate_environment,
)
from app.config.settings import settings


def test_settings_load():
    assert settings.app.name == "Trading Bot"
    assert settings.app.version == "0.1.0"


def test_environment_is_valid():
    environment = get_environment()

    assert environment in {
        Environment.DEVELOPMENT,
        Environment.TESTING,
        Environment.PRODUCTION,
    }


def test_environment_validation():
    validate_environment()