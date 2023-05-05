from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest
from titiler.xarray.factory import XarrayTilerFactory

app = FastAPI()
xarray_factory = XarrayTilerFactory()
app.include_router(xarray_factory.router)
client = TestClient(app)

def test_get_variables():
    noaa_oisst_reference = "https://ncsa.osn.xsede.org/Pangeo/pangeo-forge/pangeo-forge/aws-noaa-oisst-feedstock/aws-noaa-oisst-avhrr-only.zarr/reference.json"
    response = client.get("/variables", params={"url": noaa_oisst_reference, "reference": True})
    assert response.status_code == 200
    assert response.json() == ['anom', 'err', 'ice', 'sst']