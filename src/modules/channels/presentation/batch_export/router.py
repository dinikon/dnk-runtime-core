from fastapi import APIRouter, Depends
from src.modules.identity.presentation.auth.http.csrf import require_csrf
from src.modules.channels.presentation.http_route import ChannelsRoute
from src.modules.channels.presentation.batch_export.http.controller.start_batch_export import (
    start_batch_export,
)
from src.modules.channels.presentation.batch_export.http.response.start_batch_export import (
    StartBatchExportResponse,
)
from src.modules.channels.presentation.batch_export.http.controller.resume_batch_export import (
    resume_batch_export,
)
from src.modules.channels.presentation.batch_export.http.response.resume_batch_export import (
    ResumeBatchExportResponse,
)
from src.modules.channels.presentation.batch_export.http.controller.get_batch_export import (
    get_batch_export,
)
from src.modules.channels.presentation.batch_export.http.response.get_batch_export import (
    GetBatchExportResponse,
)
from src.modules.channels.presentation.batch_export.http.controller.get_batch_export_overview import (
    get_batch_export_overview,
)
from src.modules.channels.presentation.batch_export.http.response.get_batch_export_overview import (
    GetBatchExportOverviewResponse,
)
from src.modules.channels.presentation.batch_export.http.controller.update_export_schedule import (
    update_export_schedule,
)
from src.modules.channels.presentation.batch_export.http.response.update_export_schedule import (
    UpdateExportScheduleResponse,
)
from src.modules.channels.presentation.batch_export.http.controller.set_publication_export import (
    set_publication_export,
)
from src.modules.channels.presentation.batch_export.http.response.set_publication_export import (
    SetPublicationExportResponse,
)

router = APIRouter(prefix="/channels", tags=["channels"], route_class=ChannelsRoute)
router.add_api_route(
    "/{channel_id}/batch-exports",
    start_batch_export,
    methods=["POST"],
    response_model=StartBatchExportResponse,
    status_code=202,
    dependencies=[Depends(require_csrf)],
)
router.add_api_route(
    "/batch-exports/{run_id}/resume",
    resume_batch_export,
    methods=["POST"],
    response_model=ResumeBatchExportResponse,
    status_code=202,
    dependencies=[Depends(require_csrf)],
)
router.add_api_route(
    "/batch-exports/{run_id}",
    get_batch_export,
    methods=["GET"],
    response_model=GetBatchExportResponse,
    status_code=200,
    dependencies=[],
)
router.add_api_route(
    "/{channel_id}/batch-export",
    get_batch_export_overview,
    methods=["GET"],
    response_model=GetBatchExportOverviewResponse,
    status_code=200,
    dependencies=[],
)
router.add_api_route(
    "/{channel_id}/export-schedule",
    update_export_schedule,
    methods=["PUT"],
    response_model=UpdateExportScheduleResponse,
    status_code=200,
    dependencies=[Depends(require_csrf)],
)
router.add_api_route(
    "/{channel_id}/publication-export",
    set_publication_export,
    methods=["PATCH"],
    response_model=SetPublicationExportResponse,
    status_code=200,
    dependencies=[Depends(require_csrf)],
)
