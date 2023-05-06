from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest
from titiler.xarray.factory import XarrayTilerFactory

app = FastAPI()
xarray_factory = XarrayTilerFactory()
app.include_router(xarray_factory.router)
client = TestClient(app)
DATA_DIR = 'fixtures'
def test_get_variables():
    # With reference file
    noaa_oisst_reference = f"{DATA_DIR}/reference.json"
    response = client.get("/variables", params={
        "url": noaa_oisst_reference,
        "reference": True
    })
    assert response.status_code == 200
    assert response.json() == ['anom', 'err', 'ice', 'sst']

