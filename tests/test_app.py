import json
import os

DATA_DIR = "tests/fixtures"
test_zarr_store = os.path.join(DATA_DIR, "test_zarr_store.zarr")
reference = os.path.join(DATA_DIR, "reference.json")
test_misordered_zarr_store = os.path.join(
    DATA_DIR, "test_zarr_store_misordered_coords.zarr"
)


def test_get_variables_reference(app):
    # With reference file
    response = app.get(
        "/variables",
        params={"url": reference, "reference": True, "decode_times": False},
    )
    assert response.status_code == 200
    assert response.json() == ["value"]


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


def test_get_tile(app):
    response = app.get(
        "/tiles/0/0/0.png",
        params={"url": test_zarr_store, "variable": "CDD0", "decode_times": False},
    )
    assert response.status_code == 200
    assert response.headers["Content-Type"] == "image/png"


def test_get_misordered_tile(app):
    response = app.get(
        "/tiles/0/0/0.png",
        params={
            "url": test_misordered_zarr_store,
            "variable": "CDD0",
            "decode_times": False,
        },
    )
    assert response.status_code == 200
    assert response.headers["Content-Type"] == "image/png"
