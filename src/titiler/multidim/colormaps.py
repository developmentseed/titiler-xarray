"""Custom colormaps, registered alongside rio-tiler's built-ins.

Each colormap is a 256-row table that titiler applies after ``rescale``
stretches the data to 0-255, so each one is only meaningful with the
``rescale`` listed in the README's "Custom colormaps" section.
"""

import json
from collections.abc import Mapping
from importlib.resources import files

import numpy as np
from rio_tiler.colormap import cmap as default_cmap
from rio_tiler.colormap import parse_color
from rio_tiler.types import GDALColorMapType

# The ozone ramp's color at every 10 ppb, sampled by hand from the provider's
# screenshot of the NOAA Air Quality Forecast Guidance Viewer for
# NASA-IMPACT/veda-backend#665, the pull request adding these colormaps to
# veda-backend.
O3_RAMP_PPB: dict[float, str] = {
    0: "#AFFEB0",
    10: "#7EFE7E",
    20: "#4BFF4C",
    30: "#08F001",
    40: "#03C300",
    50: "#008700",
    60: "#E1E103",
    70: "#FEBC2E",
    80: "#E17411",
    90: "#FE7879",
    100: "#BE0001",
    110: "#F0B4E7",
    120: "#DC8CD3",
    130: "#C864BF",
    140: "#B43DAB",
    150: "#A02497",
    160: "#8B1D83",
    170: "#781470",
    180: "#640D5B",
    190: "#500347",
    200: "#3C003C",
}

# EPA AQI breakpoints, as a 24-hour PM2.5 concentration (ug/m3) and as an 8-hour
# ozone concentration (ppb). Each entry after the first is where the labeled
# category ends.
PM25_UGM3_TO_O3_PPB: dict[float, float] = {
    0.0: 0.0,
    9.0: 54.0,  # Good
    35.4: 70.0,  # Moderate
    55.4: 85.0,  # Unhealthy for Sensitive Groups
    125.4: 105.0,  # Unhealthy
    225.4: 200.0,  # Very Unhealthy
}


def _colormap_from_ramp(
    ramp: Mapping[float, str], values: np.ndarray
) -> GDALColorMapType:
    """Turn ``ramp`` into a colormap with one row for each item in ``values``.

    ``ramp`` maps a few data values, its stops, to colors. Row ``i`` of the
    result is the color at ``values[i]``, blended from the colors of the two
    nearest stops when ``values[i]`` falls between them. Each colormap in this
    module passes 256 values, one for each pixel value that ``rescale``
    produces.

    >>> ramp = {0: "#000000", 10: "#FFFFFF"}  # black at 0, white at 10
    >>> _colormap_from_ramp(ramp, np.array([0, 5, 10]))
    {0: (0, 0, 0, 255), 1: (128, 128, 128, 255), 2: (255, 255, 255, 255)}
    """
    colors = np.array([parse_color(c) for c in ramp.values()])
    channels = [np.interp(values, list(ramp), channel) for channel in colors.T]
    rows = np.rint(np.stack(channels, axis=1)).astype(int).tolist()

    return dict(enumerate(map(tuple, rows)))


def _o3_equivalent_ppb(ugm3: np.ndarray) -> np.ndarray:
    """Map each PM2.5 value (ug/m3) to its ozone equivalent (ppb).

    The equivalent sits at the same relative position within the same AQI
    category, so PM2.5 and ozone in the same category get the same colors. For
    example, 22.2 ug/m3 is halfway through PM2.5's Moderate category (9.0 to
    35.4), so its equivalent is 62 ppb, halfway through ozone's (54 to 70).

    >>> _o3_equivalent_ppb(np.array([9.0, 22.2, 35.4]))
    array([54., 62., 70.])
    """
    return np.interp(
        ugm3, list(PM25_UGM3_TO_O3_PPB), list(PM25_UGM3_TO_O3_PPB.values())
    )


def worldview_rainbow_4() -> GDALColorMapType:
    """NASA Worldview custom palette "Rainbow 4", verbatim.

    The palette has 255 colors, and rio-tiler would leave a 255-row colormap's
    top value transparent, so the top color is repeated to fill 256 rows.
    """
    source = json.loads((files(__package__) / "rainbow_4.json").read_text())
    colors = [parse_color(f"#{c}") for c in source["rainbow_4"]["colors"]]

    return dict(enumerate([*colors, colors[-1]]))


def naqfc_o3() -> GDALColorMapType:
    """NAQFC ozone ramp, from 0 ppb to its top stop."""
    ppb = np.linspace(0, max(O3_RAMP_PPB), 256)

    return _colormap_from_ramp(O3_RAMP_PPB, ppb)


def naqfc_pm25() -> GDALColorMapType:
    """NAQFC PM2.5 ramp: the ozone ramp, stretched over the PM2.5 AQI categories."""
    ugm3 = np.linspace(0, max(PM25_UGM3_TO_O3_PPB), 256)

    return _colormap_from_ramp(O3_RAMP_PPB, _o3_equivalent_ppb(ugm3))


cmap = default_cmap.register(
    {
        "worldview_rainbow_4": worldview_rainbow_4(),
        "naqfc_o3": naqfc_o3(),
        "naqfc_pm25": naqfc_pm25(),
    }
)
