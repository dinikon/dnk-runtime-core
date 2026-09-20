from uuid import UUID
from fastapi import APIRouter
from src.modules.shared.presentation.identity_context.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.price_lists.presentation.depends.application import ListRunsUseCaseDep
from src.modules.price_lists.application.sync_run.query.list_runs_query import (
    ListRunsQuery,
)
from src.modules.price_lists.domain.price_list.value_object import PriceListIdVO
from src.modules.price_lists.presentation.http.boundary import (
    context_ids,
    dto_values,
    http_errors,
)
from src.modules.price_lists.presentation.http.sync_run.responses.schemas import (
    SyncRunResponse,
)

router = APIRouter()


@router.get("/{price_list_id}/runs")
async def list_runs(
    price_list_id: UUID,
    context: AuthenticatedRequestContextDep,
    use_case: ListRunsUseCaseDep,
):
    """Возвращает последние запуски выбранного прайса."""
    with http_errors():
        tenant_id, _ = context_ids(context)
        return {
            "items": [
                SyncRunResponse(**dto_values(item))
                for item in await use_case(
                    ListRunsQuery(tenant_id, PriceListIdVO.from_value(price_list_id))
                )
            ]
        }


__all__ = ["router"]
