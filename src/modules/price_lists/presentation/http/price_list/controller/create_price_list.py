from fastapi import APIRouter, Depends
from src.modules.identity.presentation.http.csrf import require_csrf
from src.modules.shared.presentation.identity_context.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.price_lists.presentation.depends.application import (
    CreatePriceListUseCaseDep,
)
from src.modules.price_lists.presentation.depends.infrastructure import (
    IdentifierGeneratorDep,
)
from src.modules.price_lists.domain.price_list.value_object import PriceListIdVO
from src.modules.price_lists.application.price_list.command.create_price_list_command import (
    CreatePriceListCommand,
)
from src.modules.price_lists.presentation.http.boundary import (
    context_ids,
    dto_values,
    http_errors,
)
from src.modules.price_lists.presentation.http.price_list.responses.schemas import (
    ActionResponse,
)
from src.modules.price_lists.presentation.http.price_list.requests.create_price_list_request import (
    CreatePriceListRequest,
)

router = APIRouter()


@router.post(
    "",
    status_code=201,
    dependencies=[Depends(require_csrf)],
    response_model=ActionResponse,
    response_model_exclude_none=True,
)
async def create_price_list(
    payload: CreatePriceListRequest,
    context: AuthenticatedRequestContextDep,
    use_case: CreatePriceListUseCaseDep,
    identifiers: IdentifierGeneratorDep,
):
    """HTTP entrypoint действия create_price_list."""
    with http_errors():
        tenant_id, actor_id = context_ids(context)
        price_list_id = identifiers.new().uuid
        values = payload.model_dump(mode="json")
        result = await use_case(
            CreatePriceListCommand(
                tenant_id=tenant_id,
                actor_id=actor_id,
                price_list_id=PriceListIdVO.from_value(price_list_id),
                **values,
            )
        )
        return ActionResponse(**dto_values(result))


__all__ = ["router"]
