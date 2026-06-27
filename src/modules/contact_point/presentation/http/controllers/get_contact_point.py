from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from src.modules.contact_point.application.query import GetContactPointQuery
from src.modules.contact_point.domain.contact_point import (
    ContactPointIdVO,
    ContactPointNotFoundError,
    ContactPointValidationError,
)
from src.modules.contact_point.presentation.depends.application import (
    GetContactPointUseCaseDep,
)
from src.modules.contact_point.presentation.http.responses import (
    ContactPointResponseSchema,
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
    "/{contact_point_id}",
    response_model=ContactPointResponseSchema,
    status_code=status.HTTP_200_OK,
)
async def get_contact_point(
    contact_point_id: UUID,
    context: AuthenticatedRequestContextDep,
    use_case: GetContactPointUseCaseDep,
) -> ContactPointResponseSchema:
    principal = context.principal
    if principal is None or principal.tenant_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized.",
        )

    try:
        result = await use_case(
            GetContactPointQuery(
                tenant_id=EntityIdVO.from_value(principal.tenant_id),
                contact_point_id=ContactPointIdVO.from_value(contact_point_id),
            )
        )
    except (ContactPointNotFoundError, RuntimeObjectNotFoundError) as exc:
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

    return ContactPointResponseSchema(
        id=result.id,
        created_at=result.created_at,
        updated_at=result.updated_at,
        contact_point_type=result.contact_point_type,
        raw_value=result.raw_value,
        normalized_value=result.normalized_value,
    )


__all__ = ["get_contact_point", "router"]
