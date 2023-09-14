"""TiTiler.xarray factory."""

from dataclasses import dataclass
from typing import Dict, List, Literal, Optional, Tuple, Type
from urllib.parse import urlencode
from starlette.templating import Jinja2Templates
import jinja2

from fastapi import Depends, Path, Query
from rio_tiler.models import Info
from starlette.requests import Request
from starlette.responses import HTMLResponse, Response

from titiler.core.dependencies import RescalingParams
from titiler.core.factory import BaseTilerFactory, img_endpoint_params
from titiler.core.models.mapbox import TileJSON
from titiler.core.resources.enums import ImageType
from titiler.core.resources.responses import JSONResponse
from titiler.xarray.reader import ZarrReader

import numpy as np

@dataclass
class ZarrTilerFactory(BaseTilerFactory):
    """Zarr Tiler Factory."""

    reader: Type[ZarrReader] = ZarrReader

    def register_routes(self) -> None:  # noqa: C901
        """Register Info / Tiles / TileJSON endoints."""

        @self.router.get(
            "/variables",
            response_class=JSONResponse,
            responses={200: {"description": "Return dataset's Variables."}},
        )
        def variable_endpoint(
            url: str = Query(..., description="Dataset URL"),
            group: Optional[int] = Query(
                None, description="Select a specific Zarr Group (Zoom Level)."
            ),
            reference: Optional[bool] = Query(
                False,
                title="reference",
                description="Whether the dataset is a kerchunk reference",
            ),
            decode_times: Optional[bool] = Query(
                True, title="decode_times", description="Whether to decode times"
            ),
        ) -> List[str]:
            """return available variables."""
            return self.reader.list_variables(url, group=group, reference=reference)

        @self.router.get(
            "/info",
            response_model=Info,
            response_model_exclude_none=True,
            response_class=JSONResponse,
            responses={200: {"description": "Return dataset's basic info."}},
        )
        def info_endpoint(
            url: str = Query(..., description="Dataset URL"),
            group: Optional[int] = Query(
                None, description="Select a specific Zarr Group (Zoom Level)."
            ),
            reference: bool = Query(
                False,
                title="reference",
                description="Whether the src_path is a kerchunk reference",
            ),
            decode_times: bool = Query(
                True, title="decode_times", description="Whether to decode times"
            ),
            variable: str = Query(..., description="Xarray Variable"),
            drop_dim: Optional[str] = Query(None, description="Dimension to drop"),
            show_times: Optional[bool] = Query(
                None, description="Show info about the time dimension"
            ),
        ) -> Info:
            """Return dataset's basic info."""
            with self.reader(
                url,
                variable=variable,
                group=group,
                reference=reference,
                decode_times=decode_times,
                drop_dim=drop_dim,
            ) as src_dst:
                info = src_dst.info().dict()
                if show_times and "time" in src_dst.input.dims:
                    times = [str(x.data) for x in src_dst.input.time]
                    info["count"] = len(times)
                    info["times"] = times

            return Info(**info)

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
            url: str = Query(..., description="Dataset URL"),
            multiscale: Optional[bool] = Query(
                False,
                title="multiscale",
                description="Whether the dataset has multiscale groups (Zoom levels)",
            ),
            reference: bool = Query(
                False,
                title="reference",
                description="Whether the src_path is a kerchunk reference",
            ),
            decode_times: bool = Query(
                True, title="decode_times", description="Whether to decode times"
            ),
            variable: str = Query(..., description="Xarray Variable"),
            drop_dim: Optional[str] = Query(None, description="Dimension to drop"),
            time_slice: str = Query(
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
        ) -> Response:
            """Create map tile from a dataset."""
            tms = self.supported_tms.get(TileMatrixSetId)

            with self.reader(
                url,
                variable=variable,
                group=z if multiscale else None,
                reference=reference,
                decode_times=decode_times,
                drop_dim=drop_dim,
                time_slice=time_slice,
                tms=tms,
            ) as src_dst:
                image = src_dst.tile(
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
            url: str = Query(..., description="Dataset URL"),
            group: Optional[int] = Query(
                None, description="Select a specific Zarr Group (Zoom Level)."
            ),
            multiscale: bool = Query(  # noqa
                False,
                title="multiscale",
                description="Whether the dataset has multiscale groups (Zoom levels)",
            ),
            reference: bool = Query(
                False,
                title="reference",
                description="Whether the src_path is a kerchunk reference",
            ),
            decode_times: bool = Query(
                True, title="decode_times", description="Whether to decode times"
            ),
            variable: str = Query(..., description="Xarray Variable"),
            drop_dim: Optional[str] = Query(
                None, description="Dimension to drop"
            ),  # noqa
            time_slice: str = Query(
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
                "group",
            ]
            qs = [
                (key, value)
                for (key, value) in request.query_params._list
                if key.lower() not in qs_key_to_remove
            ]
            if qs:
                tiles_url += f"?{urlencode(qs)}"

            tms = self.supported_tms.get(TileMatrixSetId)

            with self.reader(
                url,
                variable=variable,
                group=group,
                reference=reference,
                decode_times=decode_times,
                tms=tms,
            ) as src_dst:
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


        @self.router.get(
            "/histogram",
            response_class=JSONResponse,
            responses={200: {"description": "Return histogram for this data variable"}},
            response_model_exclude_none=True,
        )
        def histogram(
            url: str = Query(..., description="Dataset URL"),
            variable: str = Query(..., description="Variable"),
            reference: Optional[bool] = Query(
                False,
                title="reference",
                description="Whether the src_path is a kerchunk reference",
            ),
        ):
            with self.reader(
                url,
                variable=variable,
                reference=reference
            ) as src_dst:           
                boolean_mask = ~np.isnan(src_dst.input)
                data_values = src_dst.input.values[boolean_mask]
                counts, values = np.histogram(data_values, bins=10)
                counts, values = counts.tolist(), values.tolist()
                buckets = list(zip(values, [values[i+1] for i in range(len(values)-1)]))
                hist_dict = []
                for idx, bucket in enumerate(buckets):
                    hist_dict.append({"bucket": bucket, "value": counts[idx]})
                return hist_dict

        @self.router.get("/map", response_class=HTMLResponse)
        @self.router.get("/{TileMatrixSetId}/map", response_class=HTMLResponse)
        def map_viewer(
            request: Request,
            TileMatrixSetId: Literal[tuple(self.supported_tms.list())] = Query(  # type: ignore
                self.default_tms,
                description=f"TileMatrixSet Name (default: '{self.default_tms}')",
            ),  # noqa
            url: Optional[str] = Query(None, description="Dataset URL"),  # noqa
            group: Optional[int] = Query(  # noqa
                None, description="Select a specific Zarr Group (Zoom Level)."
            ),
            multiscale: Optional[bool] = Query(  # noqa
                False,
                title="multiscale",
                description="Whether the dataset has multiscale groups (Zoom levels)",
            ),
            reference: Optional[bool] = Query(  # noqa
                False,
                title="reference",
                description="Whether the src_path is a kerchunk reference",
            ),
            decode_times: Optional[bool] = Query(  # noqa
                True, title="decode_times", description="Whether to decode times"
            ),
            variable: Optional[str] = Query(None, description="Xarray Variable"),  # noqa
            drop_dim: Optional[str] = Query(
                None, description="Dimension to drop"
            ),  # noqa
            time_slice: str = Query(
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
            templates = Jinja2Templates(
                directory="",
                loader=jinja2.ChoiceLoader([jinja2.PackageLoader(__package__, ".")]),
            )            
            if url:
                tilejson_url = self.url_for(
                    request, "tilejson_endpoint", TileMatrixSetId=TileMatrixSetId
                )
                if request.query_params._list:
                    tilejson_url += f"?{urlencode(request.query_params._list)}"

                tms = self.supported_tms.get(TileMatrixSetId)
                return templates.TemplateResponse(
                    name="map.html",
                    context={
                        "request": request,
                        "tilejson_endpoint": tilejson_url,
                        "tms": tms,
                        "resolutions": [tms._resolution(matrix) for matrix in tms],
                    },
                    media_type="text/html",
                )
            else:
                return templates.TemplateResponse(
                    name="map-form.html",
                    context={
                        "request": request,
                    },
                    media_type="text/html",
                )