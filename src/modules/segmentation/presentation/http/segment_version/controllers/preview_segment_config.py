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
from src.modules.segmentation.application.segment_version import (
    PreviewSegmentConfigCommand,
    SegmentVersionDslError,
    SegmentVersionEvaluationError,
    SegmentVersionEvaluationUnsupportedRelationPathError,
)
from src.modules.segmentation.presentation.depends.application import (
    PreviewSegmentConfigUseCaseDep,
)
from src.modules.segmentation.presentation.http.segment_version.requests import (
    PreviewSegmentConfigRequestSchema,
)
from src.modules.segmentation.presentation.http.segment_version.responses import (
    SegmentPreviewContactResponseSchema,
    SegmentPreviewResponseSchema,
)
from src.modules.shared import EntityIdVO
from src.modules.shared.domain.errors import DomainError
from src.modules.shared.presentation import AuthenticatedRequestContextDep

router = APIRouter(prefix="/segments", tags=["segments"])


@router.post(
    "/preview",
    response_model=SegmentPreviewResponseSchema,
)
async def preview_segment_config(
    payload: PreviewSegmentConfigRequestSchema,
    context: AuthenticatedRequestContextDep,
    use_case: PreviewSegmentConfigUseCaseDep,
) -> SegmentPreviewResponseSchema:
    """HTTP endpoint previewing raw Contact segment config."""
    principal = context.principal
    if principal is None or principal.tenant_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized.",
        )

    try:
        result = await use_case(
            PreviewSegmentConfigCommand(
                tenant_id=EntityIdVO.from_value(principal.tenant_id),
                config=payload.config,
                limit=payload.limit,
                offset=payload.offset,
                include_contact_summary=payload.include_contact_summary,
            )
        )
    except (
        SegmentVersionEvaluationUnsupportedRelationPathError,
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
    except (
        SegmentVersionDslError,
        SegmentVersionEvaluationError,
        RuntimeDataValidationError,
        RuntimeDataFilterError,
    ) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
    except DomainError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc

    return SegmentPreviewResponseSchema(
        contact_ids=list(result.contact_ids),
        items=[
            SegmentPreviewContactResponseSchema(
                id=item.id,
                first_name=item.first_name,
                last_name=item.last_name,
                middle_name=item.middle_name,
                status=item.status,
            )
            for item in result.contacts
        ],
        limit=result.limit,
        offset=result.offset,
        count=result.count,
        total=result.total,
        has_more=result.has_more,
    )


__all__ = ["router"]
