from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from src.modules.schema_registry.application.object_feature.command import (
    DisableObjectFeatureCommand,
    EnableObjectFeatureCommand,
)
from src.modules.schema_registry.application.object_feature.dto import (
    ObjectFeatureConfigDTO,
)
from src.modules.schema_registry.application.object_feature.query import (
    GetObjectFeatureQuery,
)
from src.modules.schema_registry.domain.object.value_object import RuntimeObjectIdVO
from src.modules.schema_registry.domain.object_feature.entity import (
    ObjectFeatureConfigEntity,
)
from src.modules.schema_registry.domain.object_feature.error import (
    ObjectFeatureConfigLockedError,
    ObjectFeatureConfigNotFoundError,
)
from src.modules.schema_registry.domain.object_feature.value_object import (
    FeatureCodeVO,
    ObjectFeatureKind,
)
from src.modules.schema_registry.presentation.depends import (
    DisableObjectFeatureUseCaseDep,
    EnableObjectFeatureUseCaseDep,
    GetObjectFeatureConfigUseCaseDep,
    ObjectFeatureConfigRepositoryDep,
)
from src.modules.shared import EntityIdVO
from src.modules.shared.depends.authentication import AuthenticatedRequestContextDep
from src.modules.shared.domain.errors import DomainError

router = APIRouter(prefix="/config/objects/features", tags=["config"])


class EnableObjectFeatureRequestSchema(BaseModel):
    """HTTP request schema включения object feature."""

    object_id: UUID
    feature_code: str
    kind: str = "standard"
    config: dict[str, Any] = Field(default_factory=dict)


class ObjectFeatureRequestSchema(BaseModel):
    """HTTP request schema чтения/выключения object feature."""

    object_id: UUID
    feature_code: str


class ListObjectFeaturesRequestSchema(BaseModel):
    """HTTP request schema списка object feature configs."""

    object_id: UUID


class ObjectFeatureConfigResponseSchema(BaseModel):
    """HTTP response schema feature config runtime-объекта."""

    id: UUID
    created_at: datetime
    updated_at: datetime
    object_id: UUID
    feature_code: str
    kind: str
    status: str
    config: dict[str, Any]
    is_locked: bool
    locked_reason: str | None


class ListObjectFeatureConfigsResponseSchema(BaseModel):
    """HTTP response schema списка feature configs runtime-объекта."""

    items: list[ObjectFeatureConfigResponseSchema]
    count: int


@router.post("/enable", response_model=ObjectFeatureConfigResponseSchema)
async def enable_object_feature(
    payload: EnableObjectFeatureRequestSchema,
    context: AuthenticatedRequestContextDep,
    use_case: EnableObjectFeatureUseCaseDep,
) -> ObjectFeatureConfigResponseSchema:
    """HTTP endpoint включения object feature."""
    tenant_id = _tenant_id_from_context(context)
    try:
        result = await use_case(
            EnableObjectFeatureCommand(
                tenant_id=tenant_id,
                object_id=RuntimeObjectIdVO.from_value(payload.object_id),
                feature_code=FeatureCodeVO(payload.feature_code),
                kind=ObjectFeatureKind.from_value(payload.kind),
                config=dict(payload.config),
            )
        )
    except ObjectFeatureConfigLockedError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except (DomainError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc

    return _dto_to_response(result)


@router.post("/disable", response_model=ObjectFeatureConfigResponseSchema)
async def disable_object_feature(
    payload: ObjectFeatureRequestSchema,
    context: AuthenticatedRequestContextDep,
    use_case: DisableObjectFeatureUseCaseDep,
) -> ObjectFeatureConfigResponseSchema:
    """HTTP endpoint выключения object feature."""
    tenant_id = _tenant_id_from_context(context)
    try:
        result = await use_case(
            DisableObjectFeatureCommand(
                tenant_id=tenant_id,
                object_id=RuntimeObjectIdVO.from_value(payload.object_id),
                feature_code=FeatureCodeVO(payload.feature_code),
            )
        )
    except ObjectFeatureConfigNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except ObjectFeatureConfigLockedError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except (DomainError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc

    return _dto_to_response(result)


@router.post("/schema", response_model=ObjectFeatureConfigResponseSchema)
async def get_object_feature_schema(
    payload: ObjectFeatureRequestSchema,
    context: AuthenticatedRequestContextDep,
    use_case: GetObjectFeatureConfigUseCaseDep,
) -> ObjectFeatureConfigResponseSchema:
    """HTTP endpoint чтения schema/config object feature."""
    tenant_id = _tenant_id_from_context(context)
    try:
        result = await use_case(
            GetObjectFeatureQuery(
                tenant_id=tenant_id,
                object_id=RuntimeObjectIdVO.from_value(payload.object_id),
                feature_code=FeatureCodeVO(payload.feature_code),
            )
        )
    except ObjectFeatureConfigNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except (DomainError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc

    return _dto_to_response(result)


@router.post("/list", response_model=ListObjectFeatureConfigsResponseSchema)
async def list_object_features(
    payload: ListObjectFeaturesRequestSchema,
    context: AuthenticatedRequestContextDep,
    repository: ObjectFeatureConfigRepositoryDep,
) -> ListObjectFeatureConfigsResponseSchema:
    """HTTP endpoint списка feature configs runtime-объекта."""
    tenant_id = _tenant_id_from_context(context)
    try:
        result = await repository.list_by_object(
            tenant_id=tenant_id,
            object_id=RuntimeObjectIdVO.from_value(payload.object_id),
        )
    except (DomainError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc

    items = [_entity_to_response(item) for item in result]
    return ListObjectFeatureConfigsResponseSchema(items=items, count=len(items))


def _tenant_id_from_context(context: AuthenticatedRequestContextDep) -> EntityIdVO:
    principal = context.principal
    if principal is None or principal.tenant_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized.",
        )
    return EntityIdVO.from_value(principal.tenant_id)


def _dto_to_response(dto: ObjectFeatureConfigDTO) -> ObjectFeatureConfigResponseSchema:
    return ObjectFeatureConfigResponseSchema(
        id=dto.id,
        created_at=dto.created_at,
        updated_at=dto.updated_at,
        object_id=dto.object_id,
        feature_code=dto.feature_code,
        kind=dto.kind,
        status=dto.status,
        config=dto.config,
        is_locked=dto.is_locked,
        locked_reason=dto.locked_reason,
    )


def _entity_to_response(
    entity: ObjectFeatureConfigEntity,
) -> ObjectFeatureConfigResponseSchema:
    return ObjectFeatureConfigResponseSchema(
        id=entity.id.uuid,
        created_at=entity.created_at,
        updated_at=entity.updated_at,
        object_id=entity.object_id.uuid,
        feature_code=entity.feature_code.value,
        kind=entity.kind.value,
        status=entity.status.value,
        config=dict(entity.config),
        is_locked=entity.is_locked,
        locked_reason=entity.locked_reason,
    )


__all__ = ["router"]
