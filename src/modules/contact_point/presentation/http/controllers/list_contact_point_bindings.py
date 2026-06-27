from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from src.modules.contact_point.application.query import ListContactPointBindingsQuery
from src.modules.contact_point.domain.binding import ContactPointBindingNotFoundError
from src.modules.contact_point.domain.contact_point import (
    ContactPointIdVO,
    ContactPointNotFoundError,
    ContactPointTypeVO,
    ContactPointValidationError,
)
from src.modules.contact_point.presentation.depends.application import (
    ListContactPointBindingsUseCaseDep,
)
from src.modules.contact_point.presentation.http.responses import (
    ContactPointBindingResponseSchema,
    ListContactPointBindingsResponseSchema,
)
from src.modules.runtime_data.domain.error import (
    RuntimeDataFilterError,
    RuntimeDataPersistenceError,
    RuntimeDataPolicyError,
    RuntimeDataValidationError,
)
from src.modules.schema_registry.domain.error import (
    RuntimeObjectDescriptorError,
    RuntimeObjectNotFoundError,
    SchemaRegistryMetadataInconsistentError,
)
from src.modules.shared import EntityIdVO
from src.modules.shared import DomainError
from src.modules.shared.presentation import AuthenticatedRequestContextDep

router = APIRouter(prefix="/contact-points", tags=["contact-points"])


@router.get(
    "/bindings",
    response_model=ListContactPointBindingsResponseSchema,
    status_code=status.HTTP_200_OK,
)
async def list_contact_point_bindings(
    context: AuthenticatedRequestContextDep,
    use_case: ListContactPointBindingsUseCaseDep,
    contact_point_type: ContactPointTypeVO | None = None,
    contact_point_id: UUID | None = None,
    owner_object_id: UUID | None = None,
    owner_record_id: UUID | None = None,
    is_active: bool | None = None,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> ListContactPointBindingsResponseSchema:
    principal = context.principal
    if principal is None or principal.tenant_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized.",
        )

    try:
        result = await use_case(
            ListContactPointBindingsQuery(
                tenant_id=EntityIdVO.from_value(principal.tenant_id),
                contact_point_type=contact_point_type,
                contact_point_id=(
                    ContactPointIdVO.from_value(contact_point_id)
                    if contact_point_id is not None
                    else None
                ),
                owner_object_id=(
                    EntityIdVO.from_value(owner_object_id)
                    if owner_object_id is not None
                    else None
                ),
                owner_record_id=(
                    EntityIdVO.from_value(owner_record_id)
                    if owner_record_id is not None
                    else None
                ),
                is_active=is_active,
                limit=limit,
                offset=offset,
            )
        )
    except (
        ContactPointBindingNotFoundError,
        ContactPointNotFoundError,
        RuntimeObjectNotFoundError,
    ) as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except (
        RuntimeDataPersistenceError,
        RuntimeDataPolicyError,
        RuntimeObjectDescriptorError,
        SchemaRegistryMetadataInconsistentError,
    ) as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except (
        ContactPointValidationError,
        RuntimeDataValidationError,
        RuntimeDataFilterError,
    ) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
    except DomainError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc

    return ListContactPointBindingsResponseSchema(
        items=[
            ContactPointBindingResponseSchema(
                id=item.id,
                contact_point_id=item.contact_point_id,
                contact_point_type=item.contact_point_type,
                owner_object_id=item.owner_object_id,
                owner_record_id=item.owner_record_id,
                is_primary=item.is_primary,
                is_active=item.is_active,
                detached_at=item.detached_at,
                created_at=item.created_at,
                updated_at=item.updated_at,
            )
            for item in result.items
        ],
        count=result.count,
        limit=result.limit,
        offset=result.offset,
    )


__all__ = ["list_contact_point_bindings", "router"]
