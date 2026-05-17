from __future__ import annotations

from typing import Protocol

from src.modules.schema_registry.application.object_feature.command import (
    DisableObjectFeatureCommand,
    EnableObjectFeatureCommand,
    UpdateObjectFeatureConfigCommand,
)
from src.modules.schema_registry.application.object_feature.dto import (
    ObjectFeatureConfigDTO,
    ObjectFeatureConfigListDTO,
)
from src.modules.schema_registry.application.object_feature.query import (
    GetObjectFeatureQuery,
    ListObjectFeaturesQuery,
)
from src.modules.schema_registry.domain.object.value_object import RuntimeObjectIdVO
from src.modules.schema_registry.domain.object_feature.value_object import FeatureCodeVO
from src.modules.shared import EntityIdVO


class EnableObjectFeatureUseCaseProtocol(Protocol):
    async def __call__(
        self,
        command: EnableObjectFeatureCommand,
    ) -> ObjectFeatureConfigDTO: ...


class DisableObjectFeatureUseCaseProtocol(Protocol):
    async def __call__(
        self,
        command: DisableObjectFeatureCommand,
    ) -> ObjectFeatureConfigDTO: ...


class UpdateObjectFeatureConfigUseCaseProtocol(Protocol):
    async def __call__(
        self,
        command: UpdateObjectFeatureConfigCommand,
    ) -> ObjectFeatureConfigDTO: ...


class GetObjectFeatureConfigUseCaseProtocol(Protocol):
    async def __call__(
        self,
        query: GetObjectFeatureQuery,
    ) -> ObjectFeatureConfigDTO: ...


class ListObjectFeaturesUseCaseProtocol(Protocol):
    async def __call__(
        self,
        query: ListObjectFeaturesQuery,
    ) -> ObjectFeatureConfigListDTO: ...


class AssertObjectFeatureEnabledUseCaseProtocol(Protocol):
    async def __call__(
        self,
        *,
        tenant_id: EntityIdVO,
        object_id: RuntimeObjectIdVO,
        feature_code: str | FeatureCodeVO,
    ) -> None: ...


__all__ = [
    "AssertObjectFeatureEnabledUseCaseProtocol",
    "DisableObjectFeatureUseCaseProtocol",
    "EnableObjectFeatureUseCaseProtocol",
    "GetObjectFeatureConfigUseCaseProtocol",
    "ListObjectFeaturesUseCaseProtocol",
    "UpdateObjectFeatureConfigUseCaseProtocol",
]
