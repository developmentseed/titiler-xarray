"""titiler app."""

import logging
import os
import shutil

import rioxarray
from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

import titiler.xarray.reader as reader
from titiler.core.errors import DEFAULT_STATUS_CODES, add_exception_handlers
from titiler.core.factory import AlgorithmFactory, TMSFactory
from titiler.core.middleware import (
    CacheControlMiddleware,
    LoggerMiddleware,
    TotalTimeMiddleware,
)
from titiler.xarray import __version__ as titiler_version
from titiler.xarray.factory import ZarrTilerFactory
from titiler.xarray.middleware import ServerTimingMiddleware
from titiler.xarray.settings import ApiSettings

logging.getLogger("botocore.credentials").disabled = True
logging.getLogger("botocore.utils").disabled = True
logging.getLogger("rio-tiler").setLevel(logging.ERROR)

api_settings = ApiSettings()

app = FastAPI(
    title=api_settings.name,
    openapi_url="/api",
    docs_url="/api.html",
    version=titiler_version,
    root_path=api_settings.root_path,
)

###############################################################################
# Tiles endpoints
xarray_factory = ZarrTilerFactory()
app.include_router(xarray_factory.router, tags=["Xarray Tiler API"])

###############################################################################
# TileMatrixSets endpoints
tms = TMSFactory()
app.include_router(tms.router, tags=["Tiling Schemes"])

###############################################################################
# Algorithms endpoints
algorithms = AlgorithmFactory()
app.include_router(algorithms.router, tags=["Algorithms"])

add_exception_handlers(app, DEFAULT_STATUS_CODES)

# Set all CORS enabled origins
if api_settings.cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=api_settings.cors_origins,
        allow_credentials=True,
        allow_methods=api_settings.cors_allow_methods,
        allow_headers=["*"],
    )

app.add_middleware(
    CacheControlMiddleware,
    cachecontrol=api_settings.cachecontrol,
    exclude_path={r"/healthz"},
)

if api_settings.debug:
    app.add_middleware(LoggerMiddleware, headers=True, querystrings=True)
    app.add_middleware(TotalTimeMiddleware)
    app.add_middleware(
        ServerTimingMiddleware,
        calls_to_track={
            "1-xarray-open_dataset": (reader.xarray_open_dataset,),
            "2-rioxarray-reproject": (rioxarray.raster_array.RasterArray.reproject,),
        },
    )


@app.get(
    "/healthz",
    description="Health Check.",
    summary="Health Check.",
    operation_id="healthCheck",
    tags=["Health Check"],
)
def ping():
    """Health check."""
    return {"ping": "pong!"}


@app.get(
    "/clear_cache",
    description="Clear Cache",
    summary="Clear Cache.",
    operation_id="clear cache",
    tags=["Clear Cache"],
)
def clear_cache():
    """
    Clear the cache.
    """
    print("Clearing the cache...")
    cache_dir = os.path.expanduser(api_settings.diskcache_directory)
    if os.path.exists(cache_dir):
        # Iterate over each directory and file in the root of the EFS
        for root_dir, dirs, files in os.walk(cache_dir, topdown=False):
            for name in files:
                file_path = os.path.join(root_dir, name)
                os.remove(file_path)
                print(f"Deleted file: {file_path}")

            for name in dirs:
                dir_path = os.path.join(root_dir, name)
                shutil.rmtree(dir_path)
                print(f"Deleted directory: {dir_path}")
    return {"message": "cache cleared"}
