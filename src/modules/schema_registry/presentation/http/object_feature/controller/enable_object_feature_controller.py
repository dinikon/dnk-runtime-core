from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from src.modules.schema_registry.application.object_feature.command import (
    EnableObjectFeatureCommand,
)
from src.modules.schema_registry.domain.object.value_object import RuntimeObjectIdVO
from src.modules.schema_registry.domain.object_feature.error import (
    ObjectFeatureConfigForbiddenError,
    ObjectFeatureConfigLockedError,
    ObjectFeatureConfigNotFoundError,
)
from src.modules.schema_registry.domain.object_feature.value_object import (
    FeatureCodeVO,
)
from src.modules.schema_registry.presentation.depends import (
    EnableObjectFeatureUseCaseDep,
)
from src.modules.schema_registry.presentation.http.object_feature.request import (
    EnableObjectFeatureRequestSchema,
)
from src.modules.schema_registry.presentation.http.object_feature.response import (
    ObjectFeatureConfigResponseSchema,
)
from src.modules.shared import EntityIdVO
from src.modules.shared.presentation.identity_context.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.shared.domain.errors import DomainError

router = APIRouter(prefix="/config/objects/features", tags=["config"])


@router.post("/enable", response_model=ObjectFeatureConfigResponseSchema)
async def enable_object_feature(
    payload: EnableObjectFeatureRequestSchema,
    context: AuthenticatedRequestContextDep,
    use_case: EnableObjectFeatureUseCaseDep,
) -> ObjectFeatureConfigResponseSchema:
    """HTTP endpoint включения object feature."""
    principal = context.principal
    if principal is None or principal.tenant_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized.",
        )

    try:
        result = await use_case(
            EnableObjectFeatureCommand(
                tenant_id=EntityIdVO.from_value(principal.tenant_id),
                object_id=RuntimeObjectIdVO.from_value(payload.object_id),
                feature_code=FeatureCodeVO(payload.feature_code),
                config=dict(payload.config),
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

    return ObjectFeatureConfigResponseSchema(
        id=result.id,
        created_at=result.created_at,
        updated_at=result.updated_at,
        object_id=result.object_id,
        feature_code=result.feature_code,
        kind=result.kind,
        status=result.status,
        config=result.config,
        is_locked=result.is_locked,
        locked_reason=result.locked_reason,
    )


__all__ = ["router"]
