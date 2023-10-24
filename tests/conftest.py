"""titiler.xarray tests configuration."""

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def app(monkeypatch):
    """App fixture."""
    monkeypatch.setenv("TITILER_XARRAY_DEBUG", "TRUE")
    monkeypatch.setenv("TITILER_XARRAY_ENABLE_CACHE", "FALSE")

    from titiler.xarray.main import app

    with TestClient(app) as client:
        yield client
