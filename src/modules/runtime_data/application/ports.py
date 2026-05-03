from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, Protocol

from src.modules.runtime_data.application.models import (
    FetchPlan,
    FilterExpression,
    FilterSpec,
    PageSpec,
    SortSpec,
)
from src.modules.schema_registry.runtime import RuntimeObjectDescriptor


class RuntimeCommandGateway(Protocol):
    """Порт командной записи runtime-данных по descriptor объекта."""

    async def insert(
        self,
        *,
        descriptor: RuntimeObjectDescriptor,
        payload: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        """Создает строку runtime-объекта и возвращает нормализованную запись."""
        ...

    async def update(
        self,
        *,
        descriptor: RuntimeObjectDescriptor,
        object_id: Any,
        patch: Mapping[str, Any],
    ) -> Mapping[str, Any] | None:
        """Обновляет строку runtime-объекта по primary key или возвращает None."""
        ...

    async def delete(
        self,
        *,
        descriptor: RuntimeObjectDescriptor,
        object_id: Any,
    ) -> bool:
        """Удаляет строку runtime-объекта и сообщает, была ли она найдена."""
        ...


class RuntimeQueryGateway(Protocol):
    """Порт чтения runtime-данных по descriptor объекта."""

    async def get_by_id(
        self,
        *,
        descriptor: RuntimeObjectDescriptor,
        object_id: Any,
        fetch_plan: FetchPlan | None = None,
    ) -> Mapping[str, Any] | None:
        """Возвращает одну runtime-запись по primary key или None."""
        ...

    async def list(
        self,
        *,
        descriptor: RuntimeObjectDescriptor,
        filters: Sequence[FilterExpression] = (),
        sorting: Sequence[SortSpec] = (),
        page: PageSpec | None = None,
        fetch_plan: FetchPlan | None = None,
    ) -> list[Mapping[str, Any]]:
        """Возвращает список runtime-записей с фильтрами, сортировкой и projection."""
        ...


class RuntimeRelationLoader(Protocol):
    """Порт дозагрузки relation-данных поверх базовых runtime-строк."""

    async def load(
        self,
        *,
        descriptor: RuntimeObjectDescriptor,
        rows: Sequence[Mapping[str, Any]],
        fetch_plan: FetchPlan,
    ) -> list[Mapping[str, Any]]:
        """Обогащает runtime-строки relation-данными согласно fetch plan."""
        ...
