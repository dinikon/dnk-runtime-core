from uuid import UUID
from fastapi import APIRouter, Depends
from src.modules.identity.presentation.http.csrf import require_csrf
from src.modules.shared.presentation.identity_context.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.contact_points.presentation.depends.application import (
    UpdateContactPointLabelUseCaseDep,
)
from src.modules.contact_points.presentation.http.boundary import (
    context_ids,
    http_errors,
)
from src.modules.contact_points.presentation.http.label.requests.schemas import (
    UpdateLabelRequest,
)
from src.modules.contact_points.presentation.http.label.responses.schemas import (
    LabelResponse,
)
from src.modules.contact_points.application.label.command.update_label_command import (
    UpdateContactPointLabelCommand,
)
from src.modules.contact_points.domain.label.value_object.identifier import (
    ContactPointLabelIdVO,
)

router = APIRouter()


@router.patch(
    "/{label_id}", response_model=LabelResponse, dependencies=[Depends(require_csrf)]
)
async def update_label(
    payload: UpdateLabelRequest,
    context: AuthenticatedRequestContextDep,
    use_case: UpdateContactPointLabelUseCaseDep,
    label_id: UUID,
):
    """Изменяет настройки только от имени администратора tenant."""
    with http_errors():
        tenant_id, actor_id = context_ids(context, admin=True)
        dto = await use_case(
            UpdateContactPointLabelCommand(
                tenant_id=tenant_id,
                actor_id=actor_id,
                label_id=ContactPointLabelIdVO.from_value(label_id),
                name=payload.name,
                is_active=payload.is_active,
            )
        )
        return LabelResponse.from_dto(dto)


__all__ = ["router"]
