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
from src.modules.segmentation.application.segment_snapshot_member import (
    ListSegmentSnapshotMembersQuery,
)
from src.modules.segmentation.domain.segment_snapshot import (
    SegmentSnapshotIdVO,
    SegmentSnapshotNotFoundError,
)
from src.modules.segmentation.presentation.depends.application import (
    ListSegmentSnapshotMembersUseCaseDep,
)
from src.modules.segmentation.presentation.http.segment_snapshot_member.responses import (
    ListSegmentSnapshotMembersResponseSchema,
    SegmentSnapshotMemberContactResponseSchema,
    SegmentSnapshotMemberResponseSchema,
)
from src.modules.shared import EntityIdVO
from src.modules.shared import DomainError
from src.modules.shared.presentation import AuthenticatedRequestContextDep

router = APIRouter(
    prefix="/segments/snapshots/{segment_snapshot_id}/members",
    tags=["segments"],
)


@router.get(
    "",
    response_model=ListSegmentSnapshotMembersResponseSchema,
)
async def list_segment_snapshot_members(
    segment_snapshot_id: UUID,
    context: AuthenticatedRequestContextDep,
    use_case: ListSegmentSnapshotMembersUseCaseDep,
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    include_contact_summary: bool = Query(default=True),
) -> ListSegmentSnapshotMembersResponseSchema:
    """HTTP endpoint listing Contact segment snapshot members."""
    principal = context.principal
    if principal is None or principal.tenant_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized.",
        )

    try:
        result = await use_case(
            ListSegmentSnapshotMembersQuery(
                tenant_id=EntityIdVO.from_value(principal.tenant_id),
                segment_snapshot_id=SegmentSnapshotIdVO.from_value(segment_snapshot_id),
                limit=limit,
                offset=offset,
                include_contact_summary=include_contact_summary,
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

    return ListSegmentSnapshotMembersResponseSchema(
        items=[
            SegmentSnapshotMemberResponseSchema(
                id=item.id,
                segment_snapshot_id=item.segment_snapshot_id,
                contact_id=item.contact_id,
                position=item.position,
                created_at=item.created_at,
                contact=(
                    None
                    if item.contact is None
                    else SegmentSnapshotMemberContactResponseSchema(
                        id=item.contact.id,
                        first_name=item.contact.first_name,
                        last_name=item.contact.last_name,
                        middle_name=item.contact.middle_name,
                        status=item.contact.status,
                    )
                ),
            )
            for item in result
        ],
        count=len(result),
    )


__all__ = ["router"]
