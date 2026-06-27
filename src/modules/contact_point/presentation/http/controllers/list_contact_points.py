from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, status

from src.modules.contact_point.application.query import ListContactPointsQuery
from src.modules.contact_point.domain.contact_point import (
    ContactPointNotFoundError,
    ContactPointTypeVO,
    ContactPointValidationError,
)
from src.modules.contact_point.presentation.depends.application import (
    ListContactPointsUseCaseDep,
)
from src.modules.contact_point.presentation.http.responses import (
    ContactPointResponseSchema,
    ListContactPointsResponseSchema,
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
    "",
    response_model=ListContactPointsResponseSchema,
    status_code=status.HTTP_200_OK,
)
async def list_contact_points(
    context: AuthenticatedRequestContextDep,
    use_case: ListContactPointsUseCaseDep,
    contact_point_type: ContactPointTypeVO | None = None,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> ListContactPointsResponseSchema:
    principal = context.principal
    if principal is None or principal.tenant_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized.",
        )

    try:
        result = await use_case(
            ListContactPointsQuery(
                tenant_id=EntityIdVO.from_value(principal.tenant_id),
                contact_point_type=contact_point_type,
                limit=limit,
                offset=offset,
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

    return ListContactPointsResponseSchema(
        items=[
            ContactPointResponseSchema(
                id=item.id,
                created_at=item.created_at,
                updated_at=item.updated_at,
                contact_point_type=item.contact_point_type,
                raw_value=item.raw_value,
                normalized_value=item.normalized_value,
            )
            for item in result.items
        ],
        count=result.count,
        limit=result.limit,
        offset=result.offset,
    )


__all__ = ["list_contact_points", "router"]
