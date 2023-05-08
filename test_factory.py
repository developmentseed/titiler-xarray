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

def contains_sublist(main_list, sublist):
    if len(sublist) > len(main_list):
        return False
    # Check if the sublist exists in the main_list
    return any(main_list[i:i + len(sublist)] == sublist for i in range(len(main_list) - len(sublist) + 1))

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
    power_zarr = f"{DATA_DIR}/power_901_monthly_meteorology_utc.zarr"
    response = client.get("/variables", params={
        "url": power_zarr,
        "decode_times": False
    }) 
    assert response.status_code == 200
    sublist = ['CDD0', 'CDD10', 'CDD18_3', 'DISPH']
    main_list = response.json()
    assert contains_sublist(main_list, sublist)

# pytest test_factory.py::test_get_info
def test_get_info_reference():
    noaa_oisst_reference = f"{DATA_DIR}/noaa_oisst_reference.json"
    response = client.get("/info", params={
        "url": noaa_oisst_reference,
        "variable": "sst",
        "reference": True
    })
    print(response.json())
    assert response.status_code == 200
    with open(f"{DATA_DIR}/responses/noaa_oisst_sst_info.json") as f:
        assert response.json() == json.load(f)

def test_get_info():
    power_zarr = f"{DATA_DIR}/power_901_monthly_meteorology_utc.zarr"
    response = client.get("/info", params={
        "url": power_zarr,
        "variable": "WS50M",
        "decode_times": False
    }) 
    assert response.status_code == 200
    with open(f"{DATA_DIR}/responses/power_901_monthly_meteorology_utc_WS50M_info.json") as f:
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
    power_zarr = f"{DATA_DIR}/power_901_monthly_meteorology_utc.zarr"
    response = client.get("/tilejson.json", params={
        "url": power_zarr,
        "variable": "WS50M",
        "decode_times": False
    }) 
    assert response.status_code == 200
    with open(f"{DATA_DIR}/responses/power_901_monthly_meteorology_utc_WS50M_tilejson.json") as f:
        assert response.json() == json.load(f)

# TODO(aimee): These depend on connectivity, possible to do without?
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
    power_zarr = "s3://power-analysis-ready-datastore/power_901_monthly_meteorology_utc.zarr"
    response = client.get("/tiles/0/0/0.png", params={
        "url": power_zarr,
        "variable": "WS50M",
        "decode_times": False
    }) 
    assert response.status_code == 200
    assert response.headers['Content-Type'] == 'image/png'
