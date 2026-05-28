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
from src.modules.segmentation.application.segment_static_member import (
    AddStaticMemberCommand,
)
from src.modules.segmentation.domain.segment_definition import (
    SegmentDefinitionNotFoundError,
    SegmentIdVO,
)
from src.modules.segmentation.domain.segment_static_member import (
    SegmentStaticMemberArchivedSegmentError,
    SegmentStaticMemberContactNotFoundError,
    SegmentStaticMemberNonStaticSegmentError,
    SegmentStaticMemberSourceTypeVO,
)
from src.modules.segmentation.presentation.depends.application import (
    AddStaticMemberUseCaseDep,
)
from src.modules.segmentation.presentation.http.segment_static_member.requests import (
    AddStaticMemberRequestSchema,
)
from src.modules.segmentation.presentation.http.segment_static_member.responses import (
    ContactSummaryResponseSchema,
    StaticMemberResponseSchema,
)
from src.modules.shared import EntityIdVO
from src.modules.shared.domain.errors import DomainError
from src.modules.shared.presentation import AuthenticatedRequestContextDep

router = APIRouter(prefix="/segments/{segment_id}/static-members", tags=["segments"])


@router.post(
    "",
    response_model=StaticMemberResponseSchema,
    status_code=status.HTTP_200_OK,
)
async def add_static_member(
    segment_id: UUID,
    payload: AddStaticMemberRequestSchema,
    context: AuthenticatedRequestContextDep,
    use_case: AddStaticMemberUseCaseDep,
) -> StaticMemberResponseSchema:
    """HTTP endpoint adding Contact to a static segment."""
    principal = context.principal
    if principal is None or principal.tenant_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized.",
        )

    try:
        result = await use_case(
            AddStaticMemberCommand(
                tenant_id=EntityIdVO.from_value(principal.tenant_id),
                segment_id=SegmentIdVO.from_value(segment_id),
                contact_id=EntityIdVO.from_value(payload.contact_id),
                source_type=SegmentStaticMemberSourceTypeVO(payload.source_type),
                metadata=payload.metadata,
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

    return StaticMemberResponseSchema(
        id=result.id,
        segment_id=result.segment_id,
        contact_id=result.contact_id,
        source_type=result.source_type,
        metadata=None if result.metadata is None else dict(result.metadata),
        created_at=result.created_at,
        updated_at=result.updated_at,
        contact=(
            None
            if result.contact is None
            else ContactSummaryResponseSchema(
                id=result.contact.id,
                first_name=result.contact.first_name,
                last_name=result.contact.last_name,
                middle_name=result.contact.middle_name,
                status=result.contact.status,
            )
        ),
    )


__all__ = ["router"]
