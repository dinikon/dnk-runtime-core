from uuid import UUID
from fastapi import APIRouter, Depends, Response
from src.modules.identity.presentation.http.csrf import require_csrf
from src.modules.shared.presentation.identity_context.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.price_lists.presentation.depends.application import (
    ActivatePriceListUseCaseDep,
)
from src.modules.price_lists.presentation.depends.infrastructure import (
    IdentifierGeneratorDep,
)
from src.modules.price_lists.domain.price_list.value_object import PriceListIdVO
from src.modules.price_lists.application.price_list.command.activate_price_list_command import (
    ActivatePriceListCommand,
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
    "/{price_list_id}/activate",
    status_code=202,
    dependencies=[Depends(require_csrf)],
    response_model=ActionResponse,
    response_model_exclude_none=True,
)
async def activate_price_list(
    price_list_id: UUID,
    context: AuthenticatedRequestContextDep,
    use_case: ActivatePriceListUseCaseDep,
):
    """HTTP entrypoint действия activate_price_list."""
    with http_errors():
        tenant_id, actor_id = context_ids(context)
        values = {}
        result = await use_case(
            ActivatePriceListCommand(
                tenant_id=tenant_id,
                actor_id=actor_id,
                price_list_id=PriceListIdVO.from_value(price_list_id),
                **values,
            )
        )
        return ActionResponse(**dto_values(result))


__all__ = ["router"]
