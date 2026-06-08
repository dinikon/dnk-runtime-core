from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException, Response, status

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
    RemoveStaticMemberCommand,
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
    RemoveStaticMemberUseCaseDep,
)
from src.modules.shared import EntityIdVO
from src.modules.shared import DomainError
from src.modules.shared.presentation import AuthenticatedRequestContextDep

router = APIRouter(prefix="/segments/{segment_id}/static-members", tags=["segments"])


@router.delete(
    "/{contact_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def remove_static_member(
    segment_id: UUID,
    contact_id: UUID,
    context: AuthenticatedRequestContextDep,
    use_case: RemoveStaticMemberUseCaseDep,
) -> Response:
    """HTTP endpoint removing Contact from a static segment."""
    principal = context.principal
    if principal is None or principal.tenant_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized.",
        )

    try:
        await use_case(
            RemoveStaticMemberCommand(
                tenant_id=EntityIdVO.from_value(principal.tenant_id),
                segment_id=SegmentIdVO.from_value(segment_id),
                contact_id=EntityIdVO.from_value(contact_id),
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

    return Response(status_code=status.HTTP_204_NO_CONTENT)


__all__ = ["router"]
