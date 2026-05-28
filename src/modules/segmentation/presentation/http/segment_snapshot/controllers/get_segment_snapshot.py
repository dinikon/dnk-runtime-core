from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException, status

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
    GetSegmentSnapshotQuery,
)
from src.modules.segmentation.domain.segment_snapshot import (
    SegmentSnapshotIdVO,
    SegmentSnapshotNotFoundError,
)
from src.modules.segmentation.presentation.depends.application import (
    GetSegmentSnapshotUseCaseDep,
)
from src.modules.segmentation.presentation.http.segment_snapshot.responses import (
    SegmentSnapshotResponseSchema,
)
from src.modules.shared import EntityIdVO
from src.modules.shared.domain.errors import DomainError
from src.modules.shared.presentation import AuthenticatedRequestContextDep

router = APIRouter(
    prefix="/segments/snapshots/{segment_snapshot_id}", tags=["segments"]
)


@router.get(
    "",
    response_model=SegmentSnapshotResponseSchema,
)
async def get_segment_snapshot(
    segment_snapshot_id: UUID,
    context: AuthenticatedRequestContextDep,
    use_case: GetSegmentSnapshotUseCaseDep,
) -> SegmentSnapshotResponseSchema:
    """HTTP endpoint loading Contact segment snapshot."""
    principal = context.principal
    if principal is None or principal.tenant_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized.",
        )

    try:
        result = await use_case(
            GetSegmentSnapshotQuery(
                tenant_id=EntityIdVO.from_value(principal.tenant_id),
                segment_snapshot_id=SegmentSnapshotIdVO.from_value(segment_snapshot_id),
            )
        )
    except SegmentSnapshotNotFoundError as exc:
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

    return SegmentSnapshotResponseSchema(
        id=result.id,
        segment_id=result.segment_id,
        segment_version_id=result.segment_version_id,
        status=result.status,
        member_count=result.member_count,
        started_at=result.started_at,
        completed_at=result.completed_at,
        error_code=result.error_code,
        error_message=result.error_message,
        created_at=result.created_at,
        updated_at=result.updated_at,
    )


__all__ = ["router"]
