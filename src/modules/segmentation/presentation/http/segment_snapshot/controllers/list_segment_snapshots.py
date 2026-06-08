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
from src.modules.segmentation.application.segment_snapshot import (
    ListSegmentSnapshotsQuery,
)
from src.modules.segmentation.domain.segment_definition import (
    SegmentDefinitionNotFoundError,
    SegmentIdVO,
)
from src.modules.segmentation.presentation.depends.application import (
    ListSegmentSnapshotsUseCaseDep,
)
from src.modules.segmentation.presentation.http.segment_snapshot.responses import (
    ListSegmentSnapshotsResponseSchema,
    SegmentSnapshotResponseSchema,
)
from src.modules.shared import EntityIdVO
from src.modules.shared import DomainError
from src.modules.shared.presentation import AuthenticatedRequestContextDep

router = APIRouter(prefix="/segments/{segment_id}/snapshots", tags=["segments"])


@router.get(
    "",
    response_model=ListSegmentSnapshotsResponseSchema,
)
async def list_segment_snapshots(
    segment_id: UUID,
    context: AuthenticatedRequestContextDep,
    use_case: ListSegmentSnapshotsUseCaseDep,
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> ListSegmentSnapshotsResponseSchema:
    """HTTP endpoint listing Contact segment snapshots."""
    principal = context.principal
    if principal is None or principal.tenant_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized.",
        )

    try:
        result = await use_case(
            ListSegmentSnapshotsQuery(
                tenant_id=EntityIdVO.from_value(principal.tenant_id),
                segment_id=SegmentIdVO.from_value(segment_id),
                limit=limit,
                offset=offset,
            )
        )
    except SegmentDefinitionNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
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

    return ListSegmentSnapshotsResponseSchema(
        items=[
            SegmentSnapshotResponseSchema(
                id=item.id,
                segment_id=item.segment_id,
                segment_version_id=item.segment_version_id,
                status=item.status,
                member_count=item.member_count,
                started_at=item.started_at,
                completed_at=item.completed_at,
                error_code=item.error_code,
                error_message=item.error_message,
                created_at=item.created_at,
                updated_at=item.updated_at,
            )
            for item in result
        ],
        count=len(result),
    )


__all__ = ["router"]
