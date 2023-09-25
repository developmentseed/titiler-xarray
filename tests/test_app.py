import json
import os

from helpers import find_string_in_stream

DATA_DIR = "tests/fixtures"
test_zarr_store = os.path.join(DATA_DIR, "test_zarr_store.zarr")
reference = os.path.join(DATA_DIR, "reference.json")


def test_get_variables_reference(app):
    # With reference file
    response = app.get(
        "/variables",
        params={"url": reference, "reference": True, "decode_times": False},
    )
    assert response.status_code == 200
    assert response.json() == ["value"]
    assert response.headers["server-timing"]
    timings = response.headers["server-timing"].split(",")
    assert len(timings) == 2
    assert timings[0].startswith("total;dur=")
    assert timings[1].lstrip().startswith("1-xarray-open_dataset;dur=")


def test_get_variables(app):
    response = app.get(
        "/variables", params={"url": test_zarr_store, "decode_times": False}
    )
    assert response.status_code == 200
    sublist = ["CDD0", "DISPH", "FROST_DAYS", "GWETPROF"]
    main_list = response.json()
    assert main_list == sublist


def test_get_info_reference(app):
    response = app.get(
        "/info",
        params={
            "url": reference,
            "variable": "value",
            "reference": True,
            "decode_times": False,
        },
    )
    assert response.status_code == 200
    with open(os.path.join(DATA_DIR, "responses", "reference_info.json")) as f:
        assert response.json() == json.load(f)


def test_get_info(app):
    response = app.get(
        "/info",
        params={"url": test_zarr_store, "variable": "CDD0", "decode_times": False},
    )
    assert response.status_code == 200
    with open(os.path.join(DATA_DIR, "responses", "test_CDD0_info.json")) as f:
        assert response.json() == json.load(f)


def test_get_tilejson_reference(app):
    response = app.get(
        "/tilejson.json",
        params={
            "url": reference,
            "variable": "value",
            "reference": True,
            "decode_times": False,
        },
    )
    assert response.status_code == 200
    with open(os.path.join(DATA_DIR, "responses", "reference_tilejson.json")) as f:
        assert response.json() == json.load(f)


def test_get_tilejson(app):
    response = app.get(
        "/tilejson.json",
        params={"url": test_zarr_store, "variable": "CDD0", "decode_times": False},
    )
    assert response.status_code == 200
    with open(os.path.join(DATA_DIR, "responses", "test_CDD0_tilejson.json")) as f:
        assert response.json() == json.load(f)


def test_get_tile_reference(app):
    response = app.get(
        "/tiles/0/0/0.png",
        params={
            "url": reference,
            "variable": "value",
            "reference": True,
            "decode_times": False,
        },
    )
    assert response.status_code == 200
    assert response.headers["Content-Type"] == "image/png"
    assert response.headers["server-timing"]
    timings = response.headers["server-timing"].split(",")
    assert len(timings) == 3
    assert timings[1].lstrip().startswith("1-xarray-open_dataset;dur=")
    assert timings[2].lstrip().startswith("2-rioxarray-reproject;dur=")


def test_get_tile(app):
    response = app.get(
        "/tiles/0/0/0.png",
        params={"url": test_zarr_store, "variable": "CDD0", "decode_times": False},
    )
    assert response.status_code == 200
    assert response.headers["Content-Type"] == "image/png"


def test_histogram_error(app):
    response = app.get(
        "/histogram",
        params={"url": test_zarr_store},
    )
    assert response.status_code == 422
    assert response.json() == {
        "detail": [
            {
                "type": "missing",
                "loc": ["query", "variable"],
                "msg": "Field required",
                "input": None,
                "url": "https://errors.pydantic.dev/2.3/v/missing",
            }
        ]
    }


def test_histogram(app):
    response = app.get(
        "/histogram",
        params={"url": test_zarr_store, "variable": "CDD0"},
    )
    assert response.status_code == 200
    with open("histogram-response.json", "r") as f:
        assert response.json() == json.load(f)


def test_map_without_params(app):
    response = app.get("/map")
    assert response.status_code == 200
    assert response.headers["Content-Type"] == "text/html; charset=utf-8"
    assert find_string_in_stream(response, "Step 1: Enter the URL of your Zarr store")


def test_map_with_params(app):
    response = app.get("/map", params={"url": test_zarr_store, "variable": "CDD0"})
    assert response.status_code == 200
    assert response.headers["Content-Type"] == "text/html; charset=utf-8"
    assert find_string_in_stream(response, "<div id='map' class=\"hidden\"></div>")
