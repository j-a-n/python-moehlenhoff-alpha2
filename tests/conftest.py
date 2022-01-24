"""pytest conftest"""

import pytest


@pytest.hookimpl
def pytest_configure(config):
    """Set pytest config options"""
    config.option.asyncio_mode = "auto"
