from src.modules.contact_points.application.label.command.create_label.command import (
    CreateContactPointLabelCommand,
)
from src.modules.contact_points.domain.contact_point.value_object.value import (
    ContactPointType,
)
from src.modules.contact_points.domain.label.value_object.identifier import (
    ContactPointLabelIdVO,
)
from src.modules.contact_points.presentation.label.depends import (
    CreateContactPointLabelHandlerDep,
)
from src.modules.contact_points.presentation.label.http.boundary import (
    context_ids,
    http_errors,
)
from src.modules.contact_points.presentation.label.http.request.create_label import (
    CreateLabelRequest,
)
from src.modules.contact_points.presentation.label.http.response.create_label import (
    CreateLabelResponse,
)
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.shared.presentation.uuid.depends import UuidDep


async def create_label(
    payload: CreateLabelRequest,
    context: AuthenticatedRequestContextDep,
    handler: CreateContactPointLabelHandlerDep,
    uuid_generator: UuidDep,
) -> CreateLabelResponse:
    """Создаёт подпись от имени администратора текущего tenant."""
    with http_errors():
        tenant_id, actor_id = context_ids(context, admin=True)
        dto = await handler.execute(
            CreateContactPointLabelCommand(
                tenant_id=tenant_id,
                actor_id=actor_id,
                label_id=ContactPointLabelIdVO.from_value(uuid_generator.new()),
                type=ContactPointType(payload.type),
                name=payload.name,
            )
        )
        return CreateLabelResponse.from_dto(dto)
