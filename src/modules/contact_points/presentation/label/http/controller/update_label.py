from uuid import UUID

from src.modules.contact_points.application.label.command.update_label.command import (
    UpdateContactPointLabelCommand,
)
from src.modules.contact_points.domain.label.value_object.identifier import (
    ContactPointLabelIdVO,
)
from src.modules.contact_points.presentation.label.depends import (
    UpdateContactPointLabelHandlerDep,
)
from src.modules.contact_points.presentation.label.http.boundary import (
    context_ids,
    http_errors,
)
from src.modules.contact_points.presentation.label.http.request.update_label import (
    UpdateLabelRequest,
)
from src.modules.contact_points.presentation.label.http.response.update_label import (
    UpdateLabelResponse,
)
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)


async def update_label(
    payload: UpdateLabelRequest,
    context: AuthenticatedRequestContextDep,
    handler: UpdateContactPointLabelHandlerDep,
    label_id: UUID,
) -> UpdateLabelResponse:
    """Изменяет подпись от имени администратора текущего tenant."""
    with http_errors():
        tenant_id, actor_id = context_ids(context, admin=True)
        dto = await handler.execute(
            UpdateContactPointLabelCommand(
                tenant_id=tenant_id,
                actor_id=actor_id,
                label_id=ContactPointLabelIdVO.from_value(label_id),
                name=payload.name,
                is_active=payload.is_active,
            )
        )
        return UpdateLabelResponse.from_dto(dto)
