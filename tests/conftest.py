"""Fixtures für die HA-Tests (nur mit pytest-homeassistant-custom-component, Python >= 3.12)."""
import pytest

pytest_plugins = "pytest_homeassistant_custom_component"


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    yield
