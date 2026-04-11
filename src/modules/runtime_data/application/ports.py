from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, Protocol

from src.modules.runtime_data.application.models import (
    FetchPlan,
    FilterSpec,
    PageSpec,
    SortSpec,
)
from src.modules.schema_registry.runtime import RuntimeObjectDescriptor


class RuntimeCommandGateway(Protocol):
    async def insert(
        self,
        *,
        descriptor: RuntimeObjectDescriptor,
        payload: Mapping[str, Any],
    ) -> Mapping[str, Any]: ...

    async def update(
        self,
        *,
        descriptor: RuntimeObjectDescriptor,
        object_id: Any,
        patch: Mapping[str, Any],
    ) -> Mapping[str, Any] | None: ...

    async def delete(
        self,
        *,
        descriptor: RuntimeObjectDescriptor,
        object_id: Any,
    ) -> bool: ...


class RuntimeQueryGateway(Protocol):
    async def get_by_id(
        self,
        *,
        descriptor: RuntimeObjectDescriptor,
        object_id: Any,
        fetch_plan: FetchPlan | None = None,
    ) -> Mapping[str, Any] | None: ...

    async def list(
        self,
        *,
        descriptor: RuntimeObjectDescriptor,
        filters: Sequence[FilterSpec] = (),
        sorting: Sequence[SortSpec] = (),
        page: PageSpec | None = None,
        fetch_plan: FetchPlan | None = None,
    ) -> list[Mapping[str, Any]]: ...


class RuntimeRelationLoader(Protocol):
    async def load(
        self,
        *,
        descriptor: RuntimeObjectDescriptor,
        rows: Sequence[Mapping[str, Any]],
        fetch_plan: FetchPlan,
    ) -> list[Mapping[str, Any]]: ...
