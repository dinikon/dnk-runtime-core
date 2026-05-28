from __future__ import annotations

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
    CreateSegmentDefinitionCommand,
)
from src.modules.segmentation.domain.segment_definition import SegmentKindVO
from src.modules.segmentation.presentation.depends.application import (
    CreateSegmentDefinitionUseCaseDep,
)
from src.modules.segmentation.presentation.http.segment_definition.requests import (
    CreateSegmentDefinitionRequestSchema,
)
from src.modules.segmentation.presentation.http.segment_definition.responses import (
    SegmentDefinitionResponseSchema,
)
from src.modules.shared import EntityIdVO
from src.modules.shared.domain.errors import DomainError
from src.modules.shared.presentation import AuthenticatedRequestContextDep

router = APIRouter(tags=["segments"])


@router.post(
    "",
    response_model=SegmentDefinitionResponseSchema,
    status_code=status.HTTP_201_CREATED,
)
async def create_segment_definition(
    payload: CreateSegmentDefinitionRequestSchema,
    context: AuthenticatedRequestContextDep,
    use_case: CreateSegmentDefinitionUseCaseDep,
) -> SegmentDefinitionResponseSchema:
    """HTTP endpoint creating Contact segment definition."""
    principal = context.principal
    if principal is None or principal.tenant_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized.",
        )

    try:
        result = await use_case(
            CreateSegmentDefinitionCommand(
                tenant_id=EntityIdVO.from_value(principal.tenant_id),
                name=payload.name,
                segment_kind=SegmentKindVO(payload.segment_kind),
                description=payload.description,
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
