from fastapi import APIRouter

from src.modules.segmentation.presentation.http.segment_version.controllers import (
    activate_segment_version,
    create_segment_version,
    get_segment_version,
    list_segment_versions,
)

routers: tuple[APIRouter, ...] = (
    create_segment_version.router,
    list_segment_versions.router,
    get_segment_version.router,
    activate_segment_version.router,
)

__all__ = ["routers"]
