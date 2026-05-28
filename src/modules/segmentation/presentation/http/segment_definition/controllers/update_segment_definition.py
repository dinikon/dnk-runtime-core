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
from src.modules.segmentation.application.segment_definition import (
    UpdateSegmentDefinitionCommand,
)
from src.modules.segmentation.domain.segment_definition import (
    SegmentDefinitionArchivedError,
    SegmentDefinitionKindChangeError,
    SegmentDefinitionNotFoundError,
    SegmentIdVO,
)
from src.modules.segmentation.presentation.depends.application import (
    UpdateSegmentDefinitionUseCaseDep,
)
from src.modules.segmentation.presentation.http.segment_definition.requests import (
    UpdateSegmentDefinitionRequestSchema,
)
from src.modules.segmentation.presentation.http.segment_definition.responses import (
    SegmentDefinitionResponseSchema,
)
from src.modules.shared import EntityIdVO
from src.modules.shared.domain.errors import DomainError
from src.modules.shared.presentation import AuthenticatedRequestContextDep

router = APIRouter(prefix="/segments", tags=["segments"])


@router.patch(
    "/{segment_id}",
    response_model=SegmentDefinitionResponseSchema,
)
async def update_segment_definition(
    segment_id: UUID,
    payload: UpdateSegmentDefinitionRequestSchema,
    context: AuthenticatedRequestContextDep,
    use_case: UpdateSegmentDefinitionUseCaseDep,
) -> SegmentDefinitionResponseSchema:
    """HTTP endpoint updating Contact segment definition."""
    principal = context.principal
    if principal is None or principal.tenant_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized.",
        )

    try:
        result = await use_case(
            UpdateSegmentDefinitionCommand(
                tenant_id=EntityIdVO.from_value(principal.tenant_id),
                segment_id=SegmentIdVO.from_value(segment_id),
                name=payload.name,
                description=payload.description,
                description_provided="description" in payload.model_fields_set,
            )
        )
    except SegmentDefinitionNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except (
        SegmentDefinitionArchivedError,
        SegmentDefinitionKindChangeError,
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

    return SegmentDefinitionResponseSchema(
        id=result.id,
        name=result.name,
        segment_kind=result.segment_kind,
        status=result.status,
        description=result.description,
        archived_at=result.archived_at,
        created_at=result.created_at,
        updated_at=result.updated_at,
    )


__all__ = ["router"]
