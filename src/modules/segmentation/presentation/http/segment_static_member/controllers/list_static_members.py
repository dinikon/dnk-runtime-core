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
from src.modules.segmentation.application.segment_static_member import (
    ListStaticMembersQuery,
)
from src.modules.segmentation.domain.segment_definition import (
    SegmentDefinitionNotFoundError,
    SegmentIdVO,
)
from src.modules.segmentation.domain.segment_static_member import (
    SegmentStaticMemberArchivedSegmentError,
    SegmentStaticMemberContactNotFoundError,
    SegmentStaticMemberNonStaticSegmentError,
)
from src.modules.segmentation.presentation.depends.application import (
    ListStaticMembersUseCaseDep,
)
from src.modules.segmentation.presentation.http.segment_static_member.responses import (
    ContactSummaryResponseSchema,
    ListStaticMembersResponseSchema,
    StaticMemberResponseSchema,
)
from src.modules.shared import EntityIdVO
from src.modules.shared.domain.errors import DomainError
from src.modules.shared.presentation import AuthenticatedRequestContextDep

router = APIRouter(prefix="/segments/{segment_id}/static-members", tags=["segments"])


@router.get(
    "",
    response_model=ListStaticMembersResponseSchema,
)
async def list_static_members(
    segment_id: UUID,
    context: AuthenticatedRequestContextDep,
    use_case: ListStaticMembersUseCaseDep,
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    include_contact_summary: bool = Query(default=True),
) -> ListStaticMembersResponseSchema:
    """HTTP endpoint listing static segment members."""
    principal = context.principal
    if principal is None or principal.tenant_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized.",
        )

    try:
        result = await use_case(
            ListStaticMembersQuery(
                tenant_id=EntityIdVO.from_value(principal.tenant_id),
                segment_id=SegmentIdVO.from_value(segment_id),
                limit=limit,
                offset=offset,
                include_contact_summary=include_contact_summary,
            )
        )
    except (
        SegmentDefinitionNotFoundError,
        SegmentStaticMemberContactNotFoundError,
    ) as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except (
        SegmentStaticMemberArchivedSegmentError,
        SegmentStaticMemberNonStaticSegmentError,
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

    return ListStaticMembersResponseSchema(
        items=[
            StaticMemberResponseSchema(
                id=item.id,
                segment_id=item.segment_id,
                contact_id=item.contact_id,
                source_type=item.source_type,
                metadata=None if item.metadata is None else dict(item.metadata),
                created_at=item.created_at,
                updated_at=item.updated_at,
                contact=(
                    None
                    if item.contact is None
                    else ContactSummaryResponseSchema(
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
