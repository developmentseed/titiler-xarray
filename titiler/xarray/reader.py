"""ZarrReader."""

import contextlib
import pickle
import re
from typing import Any, Dict, List, Optional

import attr
import fsspec
import numpy
import s3fs
import xarray
from morecantile import TileMatrixSet
from pymemcache.client.base import Client
from rasterio.crs import CRS
from rio_tiler.constants import WEB_MERCATOR_TMS, WGS84_CRS
from rio_tiler.io.xarray import XarrayReader
from rio_tiler.types import BBox

from titiler.xarray.settings import ApiSettings

api_settings = ApiSettings()

from pymemcache.client.retrying import RetryingClient
from pymemcache.exceptions import MemcacheUnexpectedCloseError

# ignore_exc: True to cause the "get", "gets", "get_many" and "gets_many" calls to treat any errors as cache misses
# connect_timeout: seconds to wait for a connection to the memcached server
# timeout: seconds to wait for send or recv calls on the socket connected to memcached
base_client = Client(api_settings.cache_host, ignore_exc=True, connect_timeout=20, timeout=20)
client = RetryingClient(
    base_client,
    attempts=3,
    retry_delay=0.01,
    retry_for=[MemcacheUnexpectedCloseError]
)

def parse_prtocol(src_path: str, reference: Optional[bool] = False):
    """
    Parse protocol from path.
    """
    match = re.match(r"^(s3|https|http)", src_path)
    protocol = "file"
    if match:
        protocol = match.group(0)
    # override protocol if reference
    if reference:
        protocol = "reference"
    return protocol


def xarray_engine(src_path: str):
    """
    Parse xarray engine from path.
    """
    if src_path.endswith(".nc"):
        return "h5netcdf"
    else:
        return "zarr"


def xarray_open_dataset(
    src_path: str,
    group: Optional[Any] = None,
    reference: Optional[bool] = False,
    decode_times: Optional[bool] = True,
    consolidated: Optional[bool] = True,
) -> xarray.Dataset:
    """Open dataset."""

    # Generate a unique key for this dataset
    if api_settings.enable_cache:
        if type(group) == int:
            cache_key = f"{src_path}_{group}"
        else:
            cache_key = src_path

        # Attempt to fetch the dataset from cache
        data_bytes = client.get(cache_key)

        # If it exists in the cache, deserialize it
        if data_bytes:
            return pickle.loads(data_bytes)

    protocol = parse_prtocol(src_path, reference=reference)
    xr_engine = xarray_engine(src_path)

    # Arguments for xarray.open_dataset
    # Default args
    xr_open_args: Dict[str, Any] = {
        "decode_coords": "all",
        "decode_times": decode_times,
    }
    # Argument if we're opening a datatree
    if group:
        xr_open_args["group"] = group

    # NetCDF arguments
    if xr_engine == "h5netcdf":
        xr_open_args["engine"] = "h5netcdf"
        xr_open_args["lock"] = False
    else:
        # Zarr arguments
        xr_open_args["engine"] = "zarr"
        xr_open_args["consolidated"] = consolidated
    # Additional arguments when dealing with a reference file.
    if reference:
        xr_open_args["consolidated"] = False
        xr_open_args["backend_kwargs"] = {"consolidated": False}

    # Arguments for file handler
    file_handler = src_path
    if protocol == "s3":
        fs = s3fs.S3FileSystem()
        file_handler = s3fs.S3Map(root=src_path, s3=fs)
    elif protocol == "https" or protocol == "http":
        fs = fsspec.filesystem(protocol)
        file_handler = fs.open(src_path)
    if reference:
        fs = fsspec.filesystem(
            "reference",
            fo=src_path,
            remote_options={"anon": True},
        )
        file_handler = fs.get_mapper("")

    ds = xarray.open_dataset(file_handler, **xr_open_args)
    if api_settings.enable_cache:
        # Serialize the dataset to bytes using pickle
        data_bytes = pickle.dumps(ds)
        client.set(cache_key, data_bytes)
    return ds


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
