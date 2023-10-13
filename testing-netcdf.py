from typing import Any, Dict, List, Optional
import diskcache as dc
import fsspec
import os
import xarray
import s3fs

cache = dc.Cache(directory='./diskcache')
@cache.memoize(tag='diskcache_xarray_open_dataset')
def xarray_open_dataset(
    src_path: str,
    group: Optional[Any] = None,
    reference: Optional[bool] = False,
    decode_times: Optional[bool] = True,
    consolidated: Optional[bool] = True,
) -> xarray.Dataset:
    # cache_key = src_path
    # if cache.get(cache_key):
    #     return cache[cache_key]
    """Open dataset."""
    # Default arguments for xarray.open_dataset
    xr_open_args: Dict[str, Any] = {
        "decode_coords": "all",
        "decode_times": decode_times,
        #"cache": False
    }
    file_handler = src_path

    # NetCDF arguments 
    if src_path.endswith(".nc"):
        if src_path.startswith("s3://"):
            fs = s3fs.S3FileSystem()
            file_handler = s3fs.S3Map(root=src_path, s3=fs)
            # fsspec_args = {
            #     'cache_storage': 'fsspec_cache',
            #     'target_protocol': 's3',
            #     'remote_options': {
            #         'anon': True
            #     }
            # }
            # fs = fsspec.filesystem('filecache', **fsspec_args)            
            # file_handler = fs.open(src_path)
        xr_open_args['engine'] = "h5netcdf"
    else:
        # Zarr arguments
        xr_open_args['engine'] = "zarr"
        xr_open_args['consolidated'] = consolidated

    # Arguments for kerchunk reference
    if reference:
        fs = fsspec.filesystem(
            "reference",
            fo=src_path,
            remote_options={"anon": True},
        )
        file_handler = fs.get_mapper("")
        xr_open_args["backend_kwargs"] = {"consolidated": False}

    # Argument if we're opening a datatree
    if group:
        xr_open_args["group"] = group
    ds = xarray.open_dataset(file_handler, **xr_open_args)
    #cache.set(cache_key, ds)
    return ds


src_path = './prXin-ACCESS-CM2-ssp126_small_chunks_compressed.nc'
print(xarray_open_dataset(src_path))