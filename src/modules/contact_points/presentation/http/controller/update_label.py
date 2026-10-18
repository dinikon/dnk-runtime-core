from uuid import UUID

from src.modules.contact_points.application.command.update_label.command import (
    UpdateContactPointLabelCommand,
)
from src.modules.contact_points.domain.value_object.label_identifier import (
    ContactPointLabelIdVO,
)
from src.modules.contact_points.presentation.depends.label import (
    UpdateContactPointLabelHandlerDep,
)
from src.modules.contact_points.domain.label_error import ContactPointLabelNotFoundError
from src.modules.contact_points.application.error import (
    ContactPointPersistenceMappingError,
)
from src.modules.contact_points.presentation.http.request.update_label import (
    UpdateLabelRequest,
)
from src.modules.contact_points.presentation.http.response.update_label import (
    UpdateLabelResponse,
)
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.shared.domain.domain_error import DomainError
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError


async def update_label(
    payload: UpdateLabelRequest,
    context: AuthenticatedRequestContextDep,
    handler: UpdateContactPointLabelHandlerDep,
    label_id: UUID,
) -> UpdateLabelResponse:
    """Изменяет подпись от имени администратора текущего tenant."""
    try:
        principal = context.principal
        if principal is None or not principal.tenant_id:
            raise HTTPException(403, "Tenant context is required.")
        if "admin" not in principal.roles:
            raise HTTPException(403, "Требуются права администратора.")
        tenant_id = EntityIdVO.from_value(principal.tenant_id)
        actor_id = EntityIdVO.from_value(principal.user_id)
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
    except ContactPointLabelNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
    except DomainError as exc:
        raise HTTPException(422, str(exc)) from exc
    except IntegrityError as exc:
        raise HTTPException(409, "Конфликт контактных данных.") from exc
    except ContactPointPersistenceMappingError as exc:
        raise HTTPException(500, "Invalid persisted contact point data.") from exc
