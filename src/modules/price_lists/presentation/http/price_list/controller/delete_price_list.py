from uuid import UUID
from fastapi import APIRouter, Depends, Response
from src.modules.identity.presentation.http.csrf import require_csrf
from src.modules.shared.presentation.identity_context.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.price_lists.presentation.depends.application import (
    DeletePriceListUseCaseDep,
)
from src.modules.price_lists.presentation.depends.infrastructure import (
    IdentifierGeneratorDep,
)
from src.modules.price_lists.domain.price_list.value_object import PriceListIdVO
from src.modules.price_lists.application.price_list.command.delete_price_list_command import (
    DeletePriceListCommand,
)
from src.modules.price_lists.presentation.http.boundary import (
    context_ids,
    dto_values,
    http_errors,
)
from src.modules.price_lists.presentation.http.price_list.responses.schemas import (
    ActionResponse,
)
from src.modules.price_lists.presentation.http.price_list.requests.delete_price_list_request import (
    DeletePriceListRequest,
)

router = APIRouter()


@router.delete(
    "/{price_list_id}", status_code=204, dependencies=[Depends(require_csrf)]
)
async def delete_price_list(
    price_list_id: UUID,
    payload: DeletePriceListRequest,
    context: AuthenticatedRequestContextDep,
    use_case: DeletePriceListUseCaseDep,
):
    """HTTP entrypoint действия delete_price_list."""
    with http_errors():
        tenant_id, actor_id = context_ids(context)
        values = payload.model_dump(mode="json")
        result = await use_case(
            DeletePriceListCommand(
                tenant_id=tenant_id,
                actor_id=actor_id,
                price_list_id=PriceListIdVO.from_value(price_list_id),
                **values,
            )
        )
        return Response(status_code=204)


__all__ = ["router"]
