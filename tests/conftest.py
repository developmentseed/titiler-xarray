"""titiler.xarray tests configuration."""

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

@pytest.fixture
def app(monkeypatch):
    """App fixture."""
    monkeypatch.setenv("TITILER_XARRAY_DEBUG", "TRUE")

    from titiler.xarray.main import app

    with TestClient(app) as client:
        yield client
