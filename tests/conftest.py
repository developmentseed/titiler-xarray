"""titiler.xarray tests configuration."""

import os
import shutil

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def app(monkeypatch):
    """App fixture."""
    monkeypatch.setenv("TITILER_XARRAY_DEBUG", "TRUE")

    from titiler.xarray.main import app

    with TestClient(app) as client:
        yield client


def pytest_sessionstart(session):
    """Setup before tests run."""
    test_cache_dir = "fsspec_test_cache"
    os.environ["TITILER_XARRAY_FSSPEC_CACHE_DIRECTORY"] = test_cache_dir
    os.makedirs(test_cache_dir, exist_ok=True)


def pytest_sessionfinish(session, exitstatus):
    """Cleanup step after all tests have been run."""
    shutil.rmtree(os.environ["TITILER_XARRAY_FSSPEC_CACHE_DIRECTORY"])
    print("\nAll tests are done! Cleaning up...")
