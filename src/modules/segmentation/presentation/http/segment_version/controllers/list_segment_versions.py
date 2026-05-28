from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

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
from src.modules.segmentation.application.segment_version import (
    ListSegmentVersionsQuery,
)
from src.modules.segmentation.domain.segment_definition import SegmentIdVO
from src.modules.segmentation.presentation.depends.application import (
    ListSegmentVersionsUseCaseDep,
)
from src.modules.segmentation.presentation.http.segment_version.responses import (
    ListSegmentVersionsResponseSchema,
    SegmentVersionResponseSchema,
)
from src.modules.shared import EntityIdVO
from src.modules.shared.domain.errors import DomainError
from src.modules.shared.presentation import AuthenticatedRequestContextDep

router = APIRouter(prefix="/segments/{segment_id}/versions", tags=["segments"])


@router.get(
    "",
    response_model=ListSegmentVersionsResponseSchema,
)
async def list_segment_versions(
    segment_id: UUID,
    context: AuthenticatedRequestContextDep,
    use_case: ListSegmentVersionsUseCaseDep,
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> ListSegmentVersionsResponseSchema:
    """HTTP endpoint listing Contact segment versions."""
    principal = context.principal
    if principal is None or principal.tenant_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized.",
        )

    try:
        result = await use_case(
            ListSegmentVersionsQuery(
                tenant_id=EntityIdVO.from_value(principal.tenant_id),
                segment_id=SegmentIdVO.from_value(segment_id),
                limit=limit,
                offset=offset,
            )
        )
    except (
        RuntimeDataPersistenceError,
        RuntimeDataPolicyError,
        RuntimeObjectDescriptorError,
        RuntimeObjectNotFoundError,
        SchemaRegistryMetadataInconsistentError,
    ) as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except (RuntimeDataValidationError, RuntimeDataFilterError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
    except DomainError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc

    return ListSegmentVersionsResponseSchema(
        items=[
            SegmentVersionResponseSchema(
                id=item.id,
                segment_id=item.segment_id,
                version_number=item.version_number,
                status=item.status,
                config=dict(item.config),
                config_checksum=item.config_checksum,
                activated_at=item.activated_at,
                archived_at=item.archived_at,
                created_at=item.created_at,
                updated_at=item.updated_at,
            )
            for item in result
        ],
        count=len(result),
    )


__all__ = ["router"]
