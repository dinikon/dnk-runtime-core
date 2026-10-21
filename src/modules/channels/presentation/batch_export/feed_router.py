from src.modules.channels.presentation.http_route import ChannelsRoute
from fastapi import APIRouter
from src.modules.channels.presentation.batch_export.http.controller.get_export_feed import (
    get_export_feed,
)

router = APIRouter(
    prefix="/api/channels", tags=["channel-feeds"], route_class=ChannelsRoute
)
router.add_api_route(
    "/batch-exports/{run_id}/feed.xml", get_export_feed, methods=["GET"]
)
