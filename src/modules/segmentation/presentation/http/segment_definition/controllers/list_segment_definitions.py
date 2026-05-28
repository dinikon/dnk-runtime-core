from __future__ import annotations

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
from src.modules.segmentation.application.segment_definition import (
    ListSegmentDefinitionsQuery,
)
from src.modules.segmentation.presentation.depends.application import (
    ListSegmentDefinitionsUseCaseDep,
)
from src.modules.segmentation.presentation.http.segment_definition.responses import (
    ListSegmentDefinitionsResponseSchema,
    SegmentDefinitionResponseSchema,
)
from src.modules.shared import EntityIdVO
from src.modules.shared.domain.errors import DomainError
from src.modules.shared.presentation import AuthenticatedRequestContextDep

router = APIRouter(prefix="/segments", tags=["segments"])


@router.get(
    "",
    response_model=ListSegmentDefinitionsResponseSchema,
)
async def list_segment_definitions(
    context: AuthenticatedRequestContextDep,
    use_case: ListSegmentDefinitionsUseCaseDep,
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> ListSegmentDefinitionsResponseSchema:
    """HTTP endpoint listing Contact segment definitions."""
    principal = context.principal
    if principal is None or principal.tenant_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized.",
        )

    try:
        result = await use_case(
            ListSegmentDefinitionsQuery(
                tenant_id=EntityIdVO.from_value(principal.tenant_id),
                limit=limit,
                offset=offset,
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

    return ListSegmentDefinitionsResponseSchema(
        items=[
            SegmentDefinitionResponseSchema(
                id=item.id,
                name=item.name,
                segment_kind=item.segment_kind,
                status=item.status,
                description=item.description,
                archived_at=item.archived_at,
                created_at=item.created_at,
                updated_at=item.updated_at,
            )
            for item in result
        ],
        count=len(result),
    )


__all__ = ["router"]
