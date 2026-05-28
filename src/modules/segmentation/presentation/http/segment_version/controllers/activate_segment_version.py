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
from src.modules.segmentation.application.segment_version import (
    ActivateSegmentVersionCommand,
)
from src.modules.segmentation.domain.segment_definition import (
    SegmentDefinitionArchivedError,
    SegmentDefinitionNotFoundError,
    SegmentIdVO,
)
from src.modules.segmentation.domain.segment_version import (
    SegmentVersionIdVO,
    SegmentVersionNotFoundError,
    SegmentVersionTransitionError,
)
from src.modules.segmentation.presentation.depends.application import (
    ActivateSegmentVersionUseCaseDep,
)
from src.modules.segmentation.presentation.http.segment_version.responses import (
    SegmentVersionResponseSchema,
)
from src.modules.shared import EntityIdVO
from src.modules.shared.domain.errors import DomainError
from src.modules.shared.presentation import AuthenticatedRequestContextDep

router = APIRouter(prefix="/segments/{segment_id}/versions", tags=["segments"])


@router.post(
    "/{version_id}/activate",
    response_model=SegmentVersionResponseSchema,
)
async def activate_segment_version(
    segment_id: UUID,
    version_id: UUID,
    context: AuthenticatedRequestContextDep,
    use_case: ActivateSegmentVersionUseCaseDep,
) -> SegmentVersionResponseSchema:
    """HTTP endpoint activating Contact segment version."""
    principal = context.principal
    if principal is None or principal.tenant_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized.",
        )

    try:
        result = await use_case(
            ActivateSegmentVersionCommand(
                tenant_id=EntityIdVO.from_value(principal.tenant_id),
                segment_id=SegmentIdVO.from_value(segment_id),
                segment_version_id=SegmentVersionIdVO.from_value(version_id),
            )
        )
    except (
        SegmentDefinitionNotFoundError,
        SegmentVersionNotFoundError,
    ) as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except (
        SegmentDefinitionArchivedError,
        SegmentVersionTransitionError,
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

    return SegmentVersionResponseSchema(
        id=result.id,
        segment_id=result.segment_id,
        version_number=result.version_number,
        status=result.status,
        config=dict(result.config),
        config_checksum=result.config_checksum,
        activated_at=result.activated_at,
        archived_at=result.archived_at,
        created_at=result.created_at,
        updated_at=result.updated_at,
    )


__all__ = ["router"]
