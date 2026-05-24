from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from src.modules.schema_registry.application.object_feature.query import (
    ListObjectFeaturesQuery,
)
from src.modules.schema_registry.domain.object.value_object import RuntimeObjectIdVO
from src.modules.schema_registry.domain.object_feature.error import (
    ObjectFeatureConfigForbiddenError,
    ObjectFeatureConfigLockedError,
    ObjectFeatureConfigNotFoundError,
)
from src.modules.schema_registry.presentation.depends import (
    ListObjectFeaturesUseCaseDep,
)
from src.modules.schema_registry.presentation.http.object_feature.request import (
    ListObjectFeaturesRequestSchema,
)
from src.modules.schema_registry.presentation.http.object_feature.response import (
    ListObjectFeatureConfigsResponseSchema,
    ObjectFeatureConfigResponseSchema,
)
from src.modules.shared import EntityIdVO
from src.modules.shared.presentation.identity_context.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.shared.domain.errors import DomainError

router = APIRouter(prefix="/config/objects/features", tags=["config"])


@router.post("/list", response_model=ListObjectFeatureConfigsResponseSchema)
async def list_object_features(
    payload: ListObjectFeaturesRequestSchema,
    context: AuthenticatedRequestContextDep,
    use_case: ListObjectFeaturesUseCaseDep,
) -> ListObjectFeatureConfigsResponseSchema:
    """HTTP endpoint списка feature configs runtime-объекта."""
    principal = context.principal
    if principal is None or principal.tenant_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized.",
        )

    try:
        result = await use_case(
            ListObjectFeaturesQuery(
                tenant_id=EntityIdVO.from_value(principal.tenant_id),
                object_id=RuntimeObjectIdVO.from_value(payload.object_id),
            )
        )
    except ObjectFeatureConfigNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except (ObjectFeatureConfigForbiddenError, ObjectFeatureConfigLockedError) as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except (DomainError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc

    return ListObjectFeatureConfigsResponseSchema(
        items=[
            ObjectFeatureConfigResponseSchema(
                id=item.id,
                created_at=item.created_at,
                updated_at=item.updated_at,
                object_id=item.object_id,
                feature_code=item.feature_code,
                kind=item.kind,
                status=item.status,
                config=item.config,
                is_locked=item.is_locked,
                locked_reason=item.locked_reason,
            )
            for item in result.items
        ],
        count=result.count,
    )


__all__ = ["router"]
