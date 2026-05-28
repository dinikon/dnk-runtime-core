from fastapi import APIRouter

from src.modules.segmentation.presentation.http.segment_definition.controllers import (
    archive_segment_definition,
    create_segment_definition,
    get_segment_definition,
    list_segment_definitions,
    update_segment_definition,
)

routers: tuple[APIRouter, ...] = (
    create_segment_definition.router,
    list_segment_definitions.router,
    get_segment_definition.router,
    update_segment_definition.router,
    archive_segment_definition.router,
)

__all__ = ["routers"]
