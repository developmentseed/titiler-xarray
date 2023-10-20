"""titiler.xarray tests configuration."""

import os
import shutil

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def app(monkeypatch):
    """App fixture."""
    monkeypatch.setenv("TITILER_XARRAY_DEBUG", "TRUE")
    os.environ["TITILER_XARRAY_DISKCACHE_DIRECTORY"] = "fsspec_test_cache"

    from titiler.xarray.main import app

    with TestClient(app) as client:
        yield client


def pytest_sessionfinish(session, exitstatus):
    """Cleanup step after all tests have been run."""
    print("\nAll tests are done! Cleaning up...")
    shutil.rmtree(os.environ["TITILER_XARRAY_DISKCACHE_DIRECTORY"])
