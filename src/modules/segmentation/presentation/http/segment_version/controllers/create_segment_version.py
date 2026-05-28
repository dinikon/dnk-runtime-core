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
    CreateSegmentVersionCommand,
)
from src.modules.segmentation.domain.segment_definition import (
    SegmentDefinitionArchivedError,
    SegmentDefinitionNotFoundError,
    SegmentIdVO,
)
from src.modules.segmentation.presentation.depends.application import (
    CreateSegmentVersionUseCaseDep,
)
from src.modules.segmentation.presentation.http.segment_version.requests import (
    CreateSegmentVersionRequestSchema,
)
from src.modules.segmentation.presentation.http.segment_version.responses import (
    SegmentVersionResponseSchema,
)
from src.modules.shared import EntityIdVO
from src.modules.shared.domain.errors import DomainError
from src.modules.shared.presentation import AuthenticatedRequestContextDep

router = APIRouter(prefix="/{segment_id}/versions", tags=["segments"])


@router.post(
    "",
    response_model=SegmentVersionResponseSchema,
    status_code=status.HTTP_201_CREATED,
)
async def create_segment_version(
    segment_id: UUID,
    payload: CreateSegmentVersionRequestSchema,
    context: AuthenticatedRequestContextDep,
    use_case: CreateSegmentVersionUseCaseDep,
) -> SegmentVersionResponseSchema:
    """HTTP endpoint creating draft Contact segment version."""
    principal = context.principal
    if principal is None or principal.tenant_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized.",
        )

    try:
        result = await use_case(
            CreateSegmentVersionCommand(
                tenant_id=EntityIdVO.from_value(principal.tenant_id),
                segment_id=SegmentIdVO.from_value(segment_id),
                config=payload.config,
            )
        )
    except SegmentDefinitionNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except (
        SegmentDefinitionArchivedError,
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
