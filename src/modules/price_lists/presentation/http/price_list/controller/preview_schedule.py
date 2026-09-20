from fastapi import APIRouter, Query
from src.modules.shared.presentation.identity_context.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.price_lists.presentation.depends.application import (
    PreviewScheduleUseCaseDep,
)
from src.modules.price_lists.application.price_list.query.preview_schedule_query import (
    PreviewScheduleQuery,
)
from src.modules.price_lists.presentation.http.boundary import (
    context_ids,
    dto_values,
    http_errors,
)
from src.modules.price_lists.presentation.http.price_list.responses.schemas import (
    SchedulePreviewResponse,
)

router = APIRouter()


@router.get("/schedule-preview", response_model=SchedulePreviewResponse)
async def preview_schedule(
    context: AuthenticatedRequestContextDep,
    use_case: PreviewScheduleUseCaseDep,
    expression: str = Query(min_length=5, max_length=128),
    timezone: str = Query(default="Europe/Kyiv", max_length=64),
):
    """Показывает ближайшие запуски расписания."""
    with http_errors():
        context_ids(context)
        return SchedulePreviewResponse(
            **dto_values(await use_case(PreviewScheduleQuery(expression, timezone)))
        )


__all__ = ["router"]
