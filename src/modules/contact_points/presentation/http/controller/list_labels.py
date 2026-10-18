from typing import Literal

from src.modules.contact_points.application.query.list_labels.query import (
    ListContactPointLabelsQuery,
)
from src.modules.contact_points.domain.value_object.value import (
    ContactPointType,
)
from src.modules.contact_points.presentation.depends.label import (
    ListContactPointLabelsHandlerDep,
)
from src.modules.contact_points.domain.label_error import ContactPointLabelNotFoundError
from src.modules.contact_points.application.error import (
    ContactPointPersistenceMappingError,
)
from src.modules.contact_points.presentation.http.response.list_labels import (
    ListLabelResponse,
)
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.shared.domain.domain_error import DomainError
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError


async def list_labels(
    context: AuthenticatedRequestContextDep,
    handler: ListContactPointLabelsHandlerDep,
    type: Literal["phone", "email"] | None = None,
) -> list[ListLabelResponse]:
    """Возвращает подписи текущего tenant, включая архивные."""
    try:
        principal = context.principal
        if principal is None or not principal.tenant_id:
            raise HTTPException(403, "Tenant context is required.")
        tenant_id = EntityIdVO.from_value(principal.tenant_id)
        _ = EntityIdVO.from_value(principal.user_id)
        rows = await handler.execute(
            ListContactPointLabelsQuery(
                tenant_id, ContactPointType(type) if type else None
            )
        )
        return [ListLabelResponse.from_dto(row) for row in rows]
    except ContactPointLabelNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
    except DomainError as exc:
        raise HTTPException(422, str(exc)) from exc
    except IntegrityError as exc:
        raise HTTPException(409, "Конфликт контактных данных.") from exc
    except ContactPointPersistenceMappingError as exc:
        raise HTTPException(500, "Invalid persisted contact point data.") from exc
