from fastapi import FastAPI
from fastapi.testclient import TestClient
import json
import pytest
from titiler.xarray.factory import XarrayTilerFactory

app = FastAPI()
xarray_factory = XarrayTilerFactory()
app.include_router(xarray_factory.router)
client = TestClient(app)
DATA_DIR = 'fixtures'
test_zarr_store = f"{DATA_DIR}/test_zarr_store.zarr"

def test_get_variables_reference():
    # With reference file
    noaa_oisst_reference = f"{DATA_DIR}/noaa_oisst_reference.json"
    response = client.get("/variables", params={
        "url": noaa_oisst_reference,
        "reference": True
    })
    assert response.status_code == 200
    assert response.json() == ['anom', 'err', 'ice', 'sst']

def test_get_variables():
    response = client.get("/variables", params={
        "url": test_zarr_store,
        "decode_times": False
    }) 
    assert response.status_code == 200
    sublist = ['CDD0', 'DISPH', 'FROST_DAYS', 'GWETPROF']
    main_list = response.json()
    assert main_list == sublist

# pytest test_factory.py::test_get_info
def test_get_info_reference():
    noaa_oisst_reference = f"{DATA_DIR}/noaa_oisst_reference.json"
    response = client.get("/info", params={
        "url": noaa_oisst_reference,
        "variable": "sst",
        "reference": True
    })
    assert response.status_code == 200
    with open(f"{DATA_DIR}/responses/noaa_oisst_sst_info.json") as f:
        assert response.json() == json.load(f)

def test_get_info():
    response = client.get("/info", params={
        "url": test_zarr_store,
        "variable": "CDD0",
        "decode_times": False
    }) 
    assert response.status_code == 200
    with open(f"{DATA_DIR}/responses/test_CDD0_info.json") as f:
        assert response.json() == json.load(f)

def test_get_tilejson_reference():
    noaa_oisst_reference = f"{DATA_DIR}/noaa_oisst_reference.json"
    response = client.get("/tilejson.json", params={
        "url": noaa_oisst_reference,
        "variable": "sst",
        "reference": True
    })
    assert response.status_code == 200
    with open(f"{DATA_DIR}/responses/noaa_oisst_sst_tilejson.json") as f:
        assert response.json() == json.load(f)

def test_get_tilejson():
    response = client.get("/tilejson.json", params={
        "url": test_zarr_store,
        "variable": "CDD0",
        "decode_times": False
    }) 
    assert response.status_code == 200
    with open(f"{DATA_DIR}/responses/test_CDD0_tilejson.json") as f:
        assert response.json() == json.load(f)

# TODO(aimee): This depends on connectivity + access to NOAA OISST files
# We should store mock data for the kercunk reference in fixtures/.
def test_get_tile_reference():
    noaa_oisst_reference = f"{DATA_DIR}/noaa_oisst_reference.json"
    response = client.get("/tiles/0/0/0.png", params={
        "url": noaa_oisst_reference,
        "variable": "sst",
        "reference": True
    })
    assert response.status_code == 200
    assert response.headers['Content-Type'] == 'image/png'

def test_get_tile():
    response = client.get("/tiles/0/0/0.png", params={
        "url": test_zarr_store,
        "variable": "CDD0",
        "decode_times": False
    }) 
    assert response.status_code == 200
    assert response.headers['Content-Type'] == 'image/png'
