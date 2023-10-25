"""ZarrReader."""

import contextlib
import re
from typing import Any, Dict, List, Optional

import attr
import fsspec
import numpy
import s3fs
import xarray
from morecantile import TileMatrixSet
from rasterio.crs import CRS
from rio_tiler.constants import WEB_MERCATOR_TMS, WGS84_CRS
from rio_tiler.io.xarray import XarrayReader
from rio_tiler.types import BBox

import diskcache as dc
from titiler.xarray.settings import ApiSettings

api_settings = ApiSettings()


def parse_protocol(src_path: str, reference: Optional[bool] = False) -> str:
    """
    Parse the protocol from the source path.
    """
    match = re.match(r"^(s3|https|http)", src_path)
    if reference:
        return "reference"
    elif match:
        return match.group(0)
    else:
        return "file"


def xarray_engine(src_path: str) -> str:
    """
    Determine the xarray engine to use based on the source path.
    """
    return "h5netcdf" if src_path.endswith(".nc") else "zarr"


def get_cache_args(protocol: str) -> Dict[str, Any]:
    """
    Get the cache arguments for the given protocol.
    """
    return {
        "target_protocol": protocol,
        "cache_storage": api_settings.fsspec_cache_directory,
        "remote_options": {"anon": True},
    }


def get_reference_args(src_path: str, anon: Optional[bool]) -> Dict[str, Any]:
    """
    Get the reference arguments for the given source path.
    """
    base_args = {"fo": src_path, "remote_options": {"anon": anon}}
    if api_settings.enable_fsspec_cache:
        base_args.update(get_cache_args("file"))
    return base_args


def get_filesystem(
    src_path: str,
    protocol: str,
    enable_fsspec_cache: bool,
    reference: Optional[bool],
    anon: Optional[bool],
):
    """
    Get the filesystem for the given source path.
    """
    if protocol == "s3":
        s3_filesystem = (
            fsspec.filesystem("filecache", **get_cache_args(protocol))
            if enable_fsspec_cache
            else s3fs.S3FileSystem()
        )
        return s3fs.S3Map(root=src_path, s3=s3_filesystem)
    elif protocol in ["https", "http"]:
        fs = fsspec.filesystem(protocol)
        return (
            fs.open(
                src_path, fs=fsspec.filesystem("filecache", **get_cache_args(protocol))
            )
            if enable_fsspec_cache
            else fs.open(src_path)
        )
    elif reference:
        reference_args = get_reference_args(src_path, anon)
        return fsspec.filesystem("reference", **reference_args).get_mapper("")
    else:
        return src_path


cache = dc.Cache(  # type: ignore
    directory=api_settings.diskcache_directory,
    eviction_policy="least-frequently-used",
    max_size=2**30 * 5,  # 5 GB
)


@cache.memoize(tag="diskcache_xarray_open_dataset")
def diskcache_xarray_open_dataset(
    src_path: str, xr_open_args: Dict[str, Any]
) -> xarray.Dataset:
    """
    Open dataset using diskcache.
    """
    return xarray.open_dataset(src_path, **xr_open_args)


def xarray_open_dataset(
    src_path: str,
    group: Optional[Any] = None,
    reference: Optional[bool] = False,
    decode_times: Optional[bool] = True,
    consolidated: Optional[bool] = True,
    anon: Optional[bool] = True,
) -> xarray.Dataset:
    """
    Open dataset using xarray.
    """
    protocol = parse_protocol(src_path, reference=reference)
    xr_engine = xarray_engine(src_path)

    xr_open_args: Dict[str, Any] = {
        "decode_coords": "all",
        "decode_times": decode_times,
        "engine": xr_engine,
    }
    if xr_engine != "h5netcdf":
        xr_open_args["consolidated"] = consolidated
    if reference:
        xr_open_args["backend_kwargs"] = {"consolidated": False}
    if group:
        xr_open_args["group"] = group

    if api_settings.enable_fsspec_cache and (
        xr_engine == "h5netcdf" or consolidated is False
    ):
        if xr_engine == "h5netcdf":
            xr_open_args["lock"] = False
        file_handler = get_filesystem(src_path, protocol, False, reference, anon)
        return diskcache_xarray_open_dataset(file_handler, xr_open_args)

    file_handler = get_filesystem(
        src_path, protocol, api_settings.enable_fsspec_cache, reference, anon
    )
    return xarray.open_dataset(file_handler, **xr_open_args)


def get_variable(
    ds: xarray.Dataset,
    variable: str,
    time_slice: Optional[str] = None,
    drop_dim: Optional[str] = None,
) -> xarray.DataArray:
    """Get Xarray variable as DataArray."""
    da = ds[variable]
    latitude_var_name = "lat"
    longitude_var_name = "lon"
    if ds.dims.get("latitude"):
        latitude_var_name = "latitude"
    if ds.dims.get("longitude"):
        longitude_var_name = "longitude"
    da = da.rename({latitude_var_name: "y", longitude_var_name: "x"})

    # TODO: add test
    if drop_dim:
        dim_to_drop, dim_val = drop_dim.split("=")
        da = da.sel({dim_to_drop: dim_val}).drop(dim_to_drop)

    if (da.x > 180).any():
        # Adjust the longitude coordinates to the -180 to 180 range
        da = da.assign_coords(x=(da.x + 180) % 360 - 180)

        # Sort the dataset by the updated longitude coordinates
        da = da.sortby(da.x)

    # Make sure we have a valid CRS
    crs = da.rio.crs or "epsg:4326"
    da.rio.write_crs(crs, inplace=True)

    # TODO - address this time_slice issue
    if "time" in da.dims:
        if time_slice:
            time_as_str = time_slice.split("T")[0]
            # TODO(aimee): when do we actually need multiple slices of data?
            # Perhaps if aggregating for coverage?
            # ds = ds[time_slice : time_slice + 1]
            if da["time"].dtype == "O":
                da["time"] = da["time"].astype("datetime64[ns]")
            da = da.sel(
                time=numpy.array(time_as_str, dtype=numpy.datetime64), method="nearest"
            )
        else:
            da = da.isel(time=0)

    return da


@attr.s
class ZarrReader(XarrayReader):
    """ZarrReader: Open Zarr file and access DataArray."""

    src_path: str = attr.ib()
    variable: str = attr.ib()

    # xarray.Dataset options
    reference: bool = attr.ib(default=False)
    decode_times: bool = attr.ib(default=False)
    group: Optional[Any] = attr.ib(default=None)
    consolidated: Optional[bool] = attr.ib(default=True)
    anon: Optional[bool] = attr.ib(default=True)

    # xarray.DataArray options
    time_slice: Optional[str] = attr.ib(default=None)
    drop_dim: Optional[str] = attr.ib(default=None)

    tms: TileMatrixSet = attr.ib(default=WEB_MERCATOR_TMS)
    geographic_crs: CRS = attr.ib(default=WGS84_CRS)

    ds: xarray.Dataset = attr.ib(init=False)
    input: xarray.DataArray = attr.ib(init=False)

    bounds: BBox = attr.ib(init=False)
    crs: CRS = attr.ib(init=False)

    _minzoom: int = attr.ib(init=False, default=None)
    _maxzoom: int = attr.ib(init=False, default=None)

    _dims: List = attr.ib(init=False, factory=list)
    _ctx_stack = attr.ib(init=False, factory=contextlib.ExitStack)

    def __attrs_post_init__(self):
        """Set bounds and CRS."""
        self.ds = self._ctx_stack.enter_context(
            xarray_open_dataset(
                self.src_path,
                group=self.group,
                reference=self.reference,
                consolidated=self.consolidated,
                anon=self.anon,
            ),
        )
        self.input = get_variable(
            self.ds,
            self.variable,
            time_slice=self.time_slice,
            drop_dim=self.drop_dim,
        )

        self.bounds = tuple(self.input.rio.bounds())
        self.crs = self.input.rio.crs

        self._dims = [
            d
            for d in self.input.dims
            if d not in [self.input.rio.x_dim, self.input.rio.y_dim]
        ]

    @classmethod
    def list_variables(
        cls,
        src_path: str,
        group: Optional[Any] = None,
        reference: Optional[bool] = False,
        consolidated: Optional[bool] = True,
    ) -> List[str]:
        """List available variable in a dataset."""
        with xarray_open_dataset(
            src_path,
            group=group,
            reference=reference,
            consolidated=consolidated,
        ) as ds:
            return list(ds.data_vars)  # type: ignore
