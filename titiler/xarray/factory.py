"""TiTiler.xarray factory."""

from dataclasses import dataclass
import fsspec
from typing import Dict, List, Literal, Optional, Tuple, Type
from urllib.parse import urlencode

import xarray
from fastapi import Depends, Path, Query
from rio_tiler.io import BaseReader, XarrayReader
from rio_tiler.models import Info
from starlette.requests import Request
from starlette.responses import HTMLResponse, Response

from titiler.core.dependencies import RescalingParams
from titiler.core.factory import BaseTilerFactory, img_endpoint_params, templates
from titiler.core.models.mapbox import TileJSON
from titiler.core.resources.enums import ImageType
from titiler.core.resources.responses import JSONResponse


@dataclass
class XarrayTilerFactory(BaseTilerFactory):
    """Xarray Tiler Factory."""

    # Default reader is set to rio_tiler.io.Reader
    reader: Type[BaseReader] = XarrayReader

    def register_routes(self) -> None:  # noqa: C901
        """Register Info / Tiles / TileJSON endoints."""

        @self.router.get(
            "/variables",
            response_class=JSONResponse,
            responses={200: {"description": "Return dataset's Variables."}},
        )
        def variable_endpoint(
            src_path: str = Depends(self.path_dependency),
        ) -> List[str]:
            """return available variables."""
            with xarray.open_dataset(
                src_path, engine="zarr", decode_coords="all"
            ) as src:
                return list(src.data_vars)  # type: ignore

        @self.router.get(
            "/info",
            response_model=Info,
            response_model_exclude_none=True,
            response_class=JSONResponse,
            responses={200: {"description": "Return dataset's basic info."}},
        )
        def info_endpoint(
            src_path: str = Depends(self.path_dependency),
            variable: str = Query(..., description="Xarray Variable"),
            show_times: bool = Query(
                None, description="Show info about the time dimension"
            ),
        ) -> Info:
            """Return dataset's basic info."""
            show_times = show_times or False

            with xarray.open_dataset(
                src_path, engine="zarr", decode_coords="all"
            ) as src:
                ds = src[variable]
                times = []
                if "time" in ds.dims:
                    times = [str(x.data) for x in ds.time]
                    # To avoid returning huge a `band_metadata` and `band_descriptions`
                    # we only return info of the first time slice
                    ds = src[variable][0]

                # Make sure we are a CRS
                crs = ds.rio.crs or "epsg:4326"
                ds.rio.write_crs(crs, inplace=True)

                with self.reader(ds) as dst:
                    info = dst.info().dict()

                if times and show_times:
                    info["count"] = len(times)
                    info["times"] = times

            return info

        @self.router.get(r"/tiles/{z}/{x}/{y}", **img_endpoint_params)
        @self.router.get(r"/tiles/{z}/{x}/{y}.{format}", **img_endpoint_params)
        @self.router.get(r"/tiles/{z}/{x}/{y}@{scale}x", **img_endpoint_params)
        @self.router.get(r"/tiles/{z}/{x}/{y}@{scale}x.{format}", **img_endpoint_params)
        @self.router.get(r"/tiles/{TileMatrixSetId}/{z}/{x}/{y}", **img_endpoint_params)
        @self.router.get(
            r"/tiles/{TileMatrixSetId}/{z}/{x}/{y}.{format}", **img_endpoint_params
        )
        @self.router.get(
            r"/tiles/{TileMatrixSetId}/{z}/{x}/{y}@{scale}x", **img_endpoint_params
        )
        @self.router.get(
            r"/tiles/{TileMatrixSetId}/{z}/{x}/{y}@{scale}x.{format}",
            **img_endpoint_params,
        )
        def tiles_endpoint(  # type: ignore
            z: int = Path(..., ge=0, le=30, description="TileMatrixSet zoom level"),
            x: int = Path(..., description="TileMatrixSet column"),
            y: int = Path(..., description="TileMatrixSet row"),
            TileMatrixSetId: Literal[  # type: ignore
                tuple(self.supported_tms.list())
            ] = Query(
                self.default_tms,
                description=f"TileMatrixSet Name (default: '{self.default_tms}')",
            ),
            scale: int = Query(
                1, gt=0, lt=4, description="Tile size scale. 1=256x256, 2=512x512..."
            ),
            format: ImageType = Query(
                None, description="Output image type. Default is auto."
            ),
            src_path: str = Depends(self.path_dependency),
            variable: str = Query(..., description="Xarray Variable"),
            time_slice: int = Query(
                None, description="Slice of time to read (if available)"
            ),
            post_process=Depends(self.process_dependency),
            rescale: Optional[List[Tuple[float, ...]]] = Depends(RescalingParams),
            color_formula: Optional[str] = Query(
                None,
                title="Color Formula",
                description=(
                    "rio-color formula (info: https://github.com/mapbox/rio-color)"
                ),
            ),
            colormap=Depends(self.colormap_dependency),
            render_params=Depends(self.render_dependency),
             multiscale: Optional[bool] = Query(False, title="multiscale", description="Whether the dataset has multiscale groups"),
            reference: Optional[bool] = Query(False, title="reference", description="Whether the src_path is a kerchunk reference"),
            drop_dim: Optional[str] = Query(None, title="drop_dim", description="Dimension to drop and value to select (e.g. zlev=0)")
        ) -> Response:
            """Create map tile from a dataset."""
            tms = self.supported_tms.get(TileMatrixSetId)
            xr_open_args = {
                'engine': 'zarr',
                'decode_coords': 'all',
                'consolidated': True
            }
            if multiscale:
                xr_open_args['group'] = z

            if reference:
                fs = fsspec.filesystem("reference", fo=src_path,
                                    remote_protocol="s3", remote_options={"anon":True})
                src_path = fs.get_mapper("")          
                xr_open_args['backend_kwargs'] = {"consolidated":False}

            with xarray.open_dataset(
                src_path, **xr_open_args
            ) as src:
                if drop_dim:
                    dim_to_drop, dim_val = drop_dim.split("=")
                    src = src.sel({dim_to_drop: dim_val}).drop(dim_to_drop)
                src = src.rename({'lat': 'y', 'lon': 'x'})

                ds = src[variable]
                if "time" in ds.dims:
                    time_slice = time_slice or 0
                    ds = ds[time_slice : time_slice + 1]

                # Make sure we are a CRS
                crs = ds.rio.crs or "epsg:4326"
                ds.rio.write_crs(crs, inplace=True)

                with self.reader(ds, tms=tms) as dst:
                    image = dst.tile(
                        x,
                        y,
                        z,
                        tilesize=scale * 256,
                    )

            if post_process:
                image = post_process(image)

            if rescale:
                image.rescale(rescale)

            if color_formula:
                image.apply_color_formula(color_formula)

            if colormap:
                image = image.apply_colormap(colormap)

            if not format:
                format = ImageType.jpeg if image.mask.all() else ImageType.png

            content = image.render(
                img_format=format.driver,
                **format.profile,
                **render_params,
            )

            return Response(content, media_type=format.mediatype)

        @self.router.get(
            "/tilejson.json",
            response_model=TileJSON,
            responses={200: {"description": "Return a tilejson"}},
            response_model_exclude_none=True,
        )
        @self.router.get(
            "/{TileMatrixSetId}/tilejson.json",
            response_model=TileJSON,
            responses={200: {"description": "Return a tilejson"}},
            response_model_exclude_none=True,
        )
        def tilejson_endpoint(  # type: ignore
            request: Request,
            TileMatrixSetId: Literal[  # type: ignore
                tuple(self.supported_tms.list())
            ] = Query(
                self.default_tms,
                description=f"TileMatrixSet Name (default: '{self.default_tms}')",
            ),
            src_path: str = Depends(self.path_dependency),
            variable: str = Query(..., description="Xarray Variable"),
            time_slice: int = Query(
                None, description="Slice of time to read (if available)"
            ),  # noqa
            tile_format: Optional[ImageType] = Query(
                None, description="Output image type. Default is auto."
            ),
            tile_scale: int = Query(
                1, gt=0, lt=4, description="Tile size scale. 1=256x256, 2=512x512..."
            ),
            minzoom: Optional[int] = Query(
                None, description="Overwrite default minzoom."
            ),
            maxzoom: Optional[int] = Query(
                None, description="Overwrite default maxzoom."
            ),
            post_process=Depends(self.process_dependency),  # noqa
            rescale: Optional[List[Tuple[float, ...]]] = Depends(
                RescalingParams
            ),  # noqa
            color_formula: Optional[str] = Query(  # noqa
                None,
                title="Color Formula",
                description=(
                    "rio-color formula (info: https://github.com/mapbox/rio-color)"
                ),
            ),
            colormap=Depends(self.colormap_dependency),  # noqa
            render_params=Depends(self.render_dependency),  # noqa
        ) -> Dict:
            """Return TileJSON document for a dataset."""
            route_params = {
                "z": "{z}",
                "x": "{x}",
                "y": "{y}",
                "scale": tile_scale,
                "TileMatrixSetId": TileMatrixSetId,
            }
            if tile_format:
                route_params["format"] = tile_format.value
            tiles_url = self.url_for(request, "tiles_endpoint", **route_params)

            qs_key_to_remove = [
                "tilematrixsetid",
                "tile_format",
                "tile_scale",
                "minzoom",
                "maxzoom",
            ]
            qs = [
                (key, value)
                for (key, value) in request.query_params._list
                if key.lower() not in qs_key_to_remove
            ]
            if qs:
                tiles_url += f"?{urlencode(qs)}"

            tms = self.supported_tms.get(TileMatrixSetId)

            with xarray.open_dataset(
                src_path, engine="zarr", decode_coords="all"
            ) as src:
                ds = src[variable]

                # Make sure we are a CRS
                crs = ds.rio.crs or "epsg:4326"
                ds.rio.write_crs(crs, inplace=True)

                with self.reader(ds, tms=tms) as src_dst:
                    # see https://github.com/corteva/rioxarray/issues/645
                    minx, miny, maxx, maxy = zip(
                        [-180, -90, 180, 90], list(src_dst.geographic_bounds)
                    )
                    bounds = [max(minx), max(miny), min(maxx), min(maxy)]
                    return {
                        "bounds": bounds,
                        "minzoom": minzoom if minzoom is not None else src_dst.minzoom,
                        "maxzoom": maxzoom if maxzoom is not None else src_dst.maxzoom,
                        "tiles": [tiles_url],
                    }

        @self.router.get("/map", response_class=HTMLResponse)
        @self.router.get("/{TileMatrixSetId}/map", response_class=HTMLResponse)
        def map_viewer(
            request: Request,
            TileMatrixSetId: Literal[tuple(self.supported_tms.list())] = Query(  # type: ignore
                self.default_tms,
                description=f"TileMatrixSet Name (default: '{self.default_tms}')",
            ),  # noqa
            src_path=Depends(self.path_dependency),  # noqa
            variable: str = Query(..., description="Xarray Variable"),  # noqa
            time_slice: int = Query(
                None, description="Slice of time to read (if available)"
            ),  # noqa
            tile_format: Optional[ImageType] = Query(
                None, description="Output image type. Default is auto."
            ),  # noqa
            tile_scale: int = Query(
                1, gt=0, lt=4, description="Tile size scale. 1=256x256, 2=512x512..."
            ),  # noqa
            minzoom: Optional[int] = Query(
                None, description="Overwrite default minzoom."
            ),  # noqa
            maxzoom: Optional[int] = Query(
                None, description="Overwrite default maxzoom."
            ),  # noqa
            layer_params=Depends(self.layer_dependency),  # noqa
            dataset_params=Depends(self.dataset_dependency),  # noqa
            post_process=Depends(self.process_dependency),  # noqa
            rescale: Optional[List[Tuple[float, ...]]] = Depends(
                RescalingParams
            ),  # noqa
            color_formula: Optional[str] = Query(  # noqa
                None,
                title="Color Formula",
                description="rio-color formula (info: https://github.com/mapbox/rio-color)",
            ),
            colormap=Depends(self.colormap_dependency),  # noqa
            render_params=Depends(self.render_dependency),  # noqa
            reader_params=Depends(self.reader_dependency),  # noqa
            env=Depends(self.environment_dependency),  # noqa
        ):
            """Return map Viewer."""
            tilejson_url = self.url_for(
                request, "tilejson_endpoint", TileMatrixSetId=TileMatrixSetId
            )
            if request.query_params._list:
                tilejson_url += f"?{urlencode(request.query_params._list)}"

            tms = self.supported_tms.get(TileMatrixSetId)
            return templates.TemplateResponse(
                name="index.html",
                context={
                    "request": request,
                    "tilejson_endpoint": tilejson_url,
                    "tms": tms,
                    "resolutions": [tms._resolution(matrix) for matrix in tms],
                },
                media_type="text/html",
            )
