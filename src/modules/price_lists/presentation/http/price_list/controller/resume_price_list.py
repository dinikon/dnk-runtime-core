from uuid import UUID
from fastapi import APIRouter, Depends
from src.modules.identity.presentation.http.csrf import require_csrf
from src.modules.shared.presentation.identity_context.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.price_lists.presentation.depends.application import (
    ResumePriceListUseCaseDep,
)
from src.modules.price_lists.domain.price_list.value_object import PriceListIdVO
from src.modules.price_lists.application.price_list.command.resume_price_list_command import (
    ResumePriceListCommand,
)
from src.modules.price_lists.presentation.http.boundary import (
    context_ids,
    dto_values,
    http_errors,
)
from src.modules.price_lists.presentation.http.price_list.responses.schemas import (
    ActionResponse,
)

router = APIRouter()


@router.post(
    "/{price_list_id}/resume",
    status_code=202,
    dependencies=[Depends(require_csrf)],
    response_model=ActionResponse,
    response_model_exclude_none=True,
)
async def resume_price_list(
    price_list_id: UUID,
    context: AuthenticatedRequestContextDep,
    use_case: ResumePriceListUseCaseDep,
):
    """HTTP entrypoint действия resume_price_list."""
    with http_errors():
        tenant_id, actor_id = context_ids(context)
        values = {}
        result = await use_case(
            ResumePriceListCommand(
                tenant_id=tenant_id,
                actor_id=actor_id,
                price_list_id=PriceListIdVO.from_value(price_list_id),
                **values,
            )
        )
        return ActionResponse(**dto_values(result))


__all__ = ["router"]
