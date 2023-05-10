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
reference = f"{DATA_DIR}/reference.json"

def test_get_variables_reference():
    # With reference file
    response = client.get("/variables", params={
        "url": reference,
        "reference": True,
        "decode_times": False
    })
    assert response.status_code == 200
    assert response.json() == ['var1', 'var2', 'var3', 'var4']

def test_get_variables():
    response = client.get("/variables", params={
        "url": test_zarr_store,
        "decode_times": False
    }) 
    assert response.status_code == 200
    sublist = ['CDD0', 'DISPH', 'FROST_DAYS', 'GWETPROF']
    main_list = response.json()
    assert main_list == sublist

def test_get_info_reference():
    response = client.get("/info", params={
        "url": reference,
        "variable": "var1",
        "reference": True,
        "decode_times": False
    })
    assert response.status_code == 200
    with open(f"{DATA_DIR}/responses/reference_info.json") as f:
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
    response = client.get("/tilejson.json", params={
        "url": reference,
        "variable": "var1",
        "reference": True,
        "decode_times": False
    })
    assert response.status_code == 200
    with open(f"{DATA_DIR}/responses/refernce_tilejson.json") as f:
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

def test_get_tile_reference():
    response = client.get("/tiles/0/0/0.png", params={
        "url": reference,
        "variable": "var1",
        "reference": True,
        "decode_times": False
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
