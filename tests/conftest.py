"""titiler.xarray tests configuration."""
from contextlib import contextmanager
import pytest
from fastapi.testclient import TestClient
from typing import Iterator
from pydantic import ValidationError

def is_recursion_validation_error(exc: ValidationError) -> bool:
    errors = exc.errors()
    return len(errors) == 1 and errors[0]['type'] == 'recursion_loop'

@pytest.fixture
def app(monkeypatch):
    """App fixture."""
    monkeypatch.setenv("TITILER_XARRAY_DEBUG", "TRUE")
    try:
        from titiler.xarray.main import app
    except Exception as exc:
        if not (is_recursion_validation_error(exc)):
            raise exc        

    with TestClient(app) as client:
        yield client
