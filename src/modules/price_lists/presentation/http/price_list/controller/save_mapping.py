from uuid import UUID
from fastapi import APIRouter, Depends, Response
from src.modules.identity.presentation.http.csrf import require_csrf
from src.modules.shared.presentation.identity_context.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.price_lists.presentation.depends.application import (
    SaveMappingUseCaseDep,
)
from src.modules.price_lists.presentation.depends.infrastructure import (
    IdentifierGeneratorDep,
)
from src.modules.price_lists.domain.price_list.value_object import PriceListIdVO
from src.modules.price_lists.application.price_list.command.save_mapping_command import (
    SaveMappingCommand,
)
from src.modules.price_lists.presentation.http.boundary import (
    context_ids,
    dto_values,
    http_errors,
)
from src.modules.price_lists.presentation.http.price_list.responses.schemas import (
    ActionResponse,
)
from src.modules.price_lists.presentation.http.price_list.requests.mapping_request import (
    MappingRequest,
)

router = APIRouter()


@router.put(
    "/{price_list_id}/mapping",
    status_code=200,
    dependencies=[Depends(require_csrf)],
    response_model=ActionResponse,
    response_model_exclude_none=True,
)
async def save_mapping(
    price_list_id: UUID,
    payload: MappingRequest,
    context: AuthenticatedRequestContextDep,
    use_case: SaveMappingUseCaseDep,
):
    """HTTP entrypoint действия save_mapping."""
    with http_errors():
        tenant_id, actor_id = context_ids(context)
        values = payload.model_dump(mode="json")
        result = await use_case(
            SaveMappingCommand(
                tenant_id=tenant_id,
                actor_id=actor_id,
                price_list_id=PriceListIdVO.from_value(price_list_id),
                **values,
            )
        )
        return ActionResponse(**dto_values(result))


__all__ = ["router"]
