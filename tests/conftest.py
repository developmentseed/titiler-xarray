"""titiler.xarray tests configuration."""

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def app():
    """App fixture."""
    from titiler.xarray.main import app

    with TestClient(app) as client:
        yield client
