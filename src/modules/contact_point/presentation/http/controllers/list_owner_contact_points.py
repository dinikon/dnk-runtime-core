from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from src.modules.contact_point.application.query import ListOwnerContactPointsQuery
from src.modules.contact_point.domain.binding import ContactPointOwnerNotFoundError
from src.modules.contact_point.domain.contact_point import (
    ContactPointNotFoundError,
    ContactPointTypeVO,
    ContactPointValidationError,
)
from src.modules.contact_point.presentation.depends.application import (
    ListOwnerContactPointsUseCaseDep,
)
from src.modules.contact_point.presentation.http.requests import (
    ListOwnerContactPointsRequestSchema,
)
from src.modules.contact_point.presentation.http.responses import (
    ListOwnerContactPointsResponseSchema,
    OwnerContactPointResponseSchema,
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
from src.modules.schema_registry.domain.object_feature import (
    ObjectFeatureConfigNotFoundError,
    ObjectFeatureNotEnabledError,
)
from src.modules.shared import EntityIdVO
from src.modules.shared.presentation import AuthenticatedRequestContextDep
from src.modules.shared.domain.errors import DomainError

router = APIRouter(prefix="/contact-points", tags=["contact-points"])


@router.post(
    "/list-by-record",
    response_model=ListOwnerContactPointsResponseSchema,
    status_code=status.HTTP_200_OK,
)
async def list_owner_contact_points(
    payload: ListOwnerContactPointsRequestSchema,
    context: AuthenticatedRequestContextDep,
    use_case: ListOwnerContactPointsUseCaseDep,
) -> ListOwnerContactPointsResponseSchema:
    principal = context.principal
    if principal is None or principal.tenant_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized.",
        )

    try:
        result = await use_case(
            ListOwnerContactPointsQuery(
                tenant_id=EntityIdVO.from_value(principal.tenant_id),
                owner_object_id=EntityIdVO.from_value(payload.owner_object_id),
                owner_record_id=EntityIdVO.from_value(payload.owner_record_id),
            )
        )
    except (
        ContactPointOwnerNotFoundError,
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
        ObjectFeatureConfigNotFoundError,
        ObjectFeatureNotEnabledError,
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

    return ListOwnerContactPointsResponseSchema(
        items=[
            OwnerContactPointResponseSchema(
                binding_id=item.binding_id,
                contact_point_id=item.contact_point_id,
                contact_point_type=item.contact_point_type,
                raw_value=item.raw_value,
                normalized_value=item.normalized_value,
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


@router.get(
    "/owners/{owner_object_id}/{owner_record_id}",
    response_model=ListOwnerContactPointsResponseSchema,
    status_code=status.HTTP_200_OK,
)
async def list_owner_contact_points_by_path(
    owner_object_id: UUID,
    owner_record_id: UUID,
    context: AuthenticatedRequestContextDep,
    use_case: ListOwnerContactPointsUseCaseDep,
    contact_point_type: ContactPointTypeVO | None = None,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> ListOwnerContactPointsResponseSchema:
    principal = context.principal
    if principal is None or principal.tenant_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized.",
        )

    try:
        result = await use_case(
            ListOwnerContactPointsQuery(
                tenant_id=EntityIdVO.from_value(principal.tenant_id),
                owner_object_id=EntityIdVO.from_value(owner_object_id),
                owner_record_id=EntityIdVO.from_value(owner_record_id),
                contact_point_type=contact_point_type,
                limit=limit,
                offset=offset,
            )
        )
    except (
        ContactPointOwnerNotFoundError,
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
        ObjectFeatureConfigNotFoundError,
        ObjectFeatureNotEnabledError,
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

    return ListOwnerContactPointsResponseSchema(
        items=[
            OwnerContactPointResponseSchema(
                binding_id=item.binding_id,
                contact_point_id=item.contact_point_id,
                contact_point_type=item.contact_point_type,
                raw_value=item.raw_value,
                normalized_value=item.normalized_value,
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


__all__ = [
    "list_owner_contact_points",
    "list_owner_contact_points_by_path",
    "router",
]
