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
    GetSegmentDefinitionQuery,
)
from src.modules.segmentation.domain.segment_definition import (
    SegmentDefinitionNotFoundError,
    SegmentIdVO,
)
from src.modules.segmentation.presentation.depends.application import (
    GetSegmentDefinitionUseCaseDep,
)
from src.modules.segmentation.presentation.http.segment_definition.responses import (
    SegmentDefinitionResponseSchema,
)
from src.modules.shared import EntityIdVO
from src.modules.shared import DomainError
from src.modules.shared.presentation import AuthenticatedRequestContextDep

router = APIRouter(prefix="/segments", tags=["segments"])


@router.get(
    "/{segment_id}",
    response_model=SegmentDefinitionResponseSchema,
)
async def get_segment_definition(
    segment_id: UUID,
    context: AuthenticatedRequestContextDep,
    use_case: GetSegmentDefinitionUseCaseDep,
) -> SegmentDefinitionResponseSchema:
    """HTTP endpoint returning Contact segment definition."""
    principal = context.principal
    if principal is None or principal.tenant_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized.",
        )

    try:
        result = await use_case(
            GetSegmentDefinitionQuery(
                tenant_id=EntityIdVO.from_value(principal.tenant_id),
                segment_id=SegmentIdVO.from_value(segment_id),
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
