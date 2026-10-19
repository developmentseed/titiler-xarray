"""Custom colormaps: the tables keep their stated properties and the API serves them."""

import json
from importlib.resources import files
from itertools import pairwise

import pytest
from test_app import store_params

from titiler.multidim import colormaps


def test_rainbow_4_is_verbatim_worldview():
    source = json.loads((files("titiler.multidim") / "rainbow_4.json").read_text())
    colors = [tuple(bytes.fromhex(c)) for c in source["rainbow_4"]["colors"]]
    rainbow = colormaps.cmap.get("worldview_rainbow_4")

    # After rescale, pixel values run from 0 to 255, and rio-tiler leaves any
    # value without a row transparent, so the colormap needs all 256 rows.
    assert len(rainbow) == 256
    # Every Worldview color in order, then the top one again to fill row 255.
    assert list(rainbow.values()) == [*colors, colors[-1]]


@pytest.mark.parametrize(
    "points",
    [
        list(colormaps.O3_RAMP_PPB),
        list(colormaps.PM25_UGM3_TO_O3_PPB),
        list(colormaps.PM25_UGM3_TO_O3_PPB.values()),
    ],
    ids=["ozone ramp", "PM2.5 breakpoints", "ozone breakpoints"],
)
def test_interpolation_points_increase(points):
    # np.interp does not check that the points it interpolates between increase,
    # so an out-of-order entry silently scrambles a colormap rather than failing.
    out_of_order = [
        f"{a} is not less than the next point, {b}"
        for a, b in pairwise(points)
        if a >= b
    ]

    assert out_of_order == []


@pytest.mark.parametrize("name", ["worldview_rainbow_4", "naqfc_o3", "naqfc_pm25"])
def test_api_lists_and_serves_custom_colormap(app, name):
    listed = {c["id"] for c in app.get("/colorMaps").json()["colormaps"]}

    assert name in listed
    assert app.get(f"/colorMaps/{name}").status_code == 200


def test_tile_renders_with_custom_colormap(app):
    params = {
        **store_params["zarr_store_v2"]["params"],
        "rescale": "0,1",
        "colormap_name": "naqfc_o3",
    }
    response = app.get("/tiles/WebMercatorQuad/0/0/0.png", params=params)

    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"
