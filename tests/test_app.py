import json
import os

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
