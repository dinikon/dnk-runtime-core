from fastapi import APIRouter, Depends
from src.modules.identity.presentation.http.csrf import require_csrf
from src.modules.shared.presentation.identity_context.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.shared.presentation.uuid.depends import UuidDep
from src.modules.contact_points.presentation.depends.application import (
    CreateContactPointLabelUseCaseDep,
)
from src.modules.contact_points.presentation.http.boundary import (
    context_ids,
    http_errors,
)
from src.modules.contact_points.presentation.http.label.requests.schemas import (
    CreateLabelRequest,
)
from src.modules.contact_points.presentation.http.label.responses.schemas import (
    LabelResponse,
)
from src.modules.contact_points.application.label.command.create_label_command import (
    CreateContactPointLabelCommand,
)
from src.modules.contact_points.domain.contact_point.value_object.value import (
    ContactPointType,
)
from src.modules.contact_points.domain.label.value_object.identifier import (
    ContactPointLabelIdVO,
)

router = APIRouter()


@router.post(
    "",
    status_code=201,
    response_model=LabelResponse,
    dependencies=[Depends(require_csrf)],
)
async def create_label(
    payload: CreateLabelRequest,
    context: AuthenticatedRequestContextDep,
    use_case: CreateContactPointLabelUseCaseDep,
    uuid_generator: UuidDep,
):
    """Изменяет настройки только от имени администратора tenant."""
    with http_errors():
        tenant_id, actor_id = context_ids(context, admin=True)
        dto = await use_case(
            CreateContactPointLabelCommand(
                tenant_id=tenant_id,
                actor_id=actor_id,
                label_id=ContactPointLabelIdVO.from_value(uuid_generator.new()),
                type=ContactPointType(payload.type),
                name=payload.name,
            )
        )
        return LabelResponse.from_dto(dto)


__all__ = ["router"]
