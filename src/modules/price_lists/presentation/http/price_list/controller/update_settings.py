from uuid import UUID
from fastapi import APIRouter, Depends, Response
from src.modules.identity.presentation.http.csrf import require_csrf
from src.modules.shared.presentation.identity_context.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.price_lists.presentation.depends.application import (
    UpdateSettingsUseCaseDep,
)
from src.modules.price_lists.presentation.depends.infrastructure import (
    IdentifierGeneratorDep,
)
from src.modules.price_lists.domain.price_list.value_object import PriceListIdVO
from src.modules.price_lists.application.price_list.command.update_settings_command import (
    UpdateSettingsCommand,
)
from src.modules.price_lists.presentation.http.boundary import (
    context_ids,
    dto_values,
    http_errors,
)
from src.modules.price_lists.presentation.http.price_list.responses.schemas import (
    ActionResponse,
)
from src.modules.price_lists.presentation.http.price_list.requests.update_price_list_settings_request import (
    UpdatePriceListSettingsRequest,
)

router = APIRouter()


@router.put(
    "/{price_list_id}/settings",
    status_code=200,
    dependencies=[Depends(require_csrf)],
    response_model=ActionResponse,
    response_model_exclude_none=True,
)
async def update_settings(
    price_list_id: UUID,
    payload: UpdatePriceListSettingsRequest,
    context: AuthenticatedRequestContextDep,
    use_case: UpdateSettingsUseCaseDep,
):
    """HTTP entrypoint действия update_settings."""
    with http_errors():
        tenant_id, actor_id = context_ids(context)
        values = payload.model_dump(mode="json")
        result = await use_case(
            UpdateSettingsCommand(
                tenant_id=tenant_id,
                actor_id=actor_id,
                price_list_id=PriceListIdVO.from_value(price_list_id),
                **values,
            )
        )
        return ActionResponse(**dto_values(result))


__all__ = ["router"]
