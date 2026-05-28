from fastapi import APIRouter
from fastapi.routing import APIRoute

from src.modules.segmentation.presentation.http.segment_definition import controllers

router = APIRouter(prefix="/segments", tags=["segments"])
for controller_router in controllers.routers:
    for route in controller_router.routes:
        if isinstance(route, APIRoute):
            router.add_api_route(
                route.path,
                route.endpoint,
                response_model=route.response_model,
                status_code=route.status_code,
                methods=route.methods,
                tags=route.tags,
                name=route.name,
            )

__all__ = ["router"]
