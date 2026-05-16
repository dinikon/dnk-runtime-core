from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, Protocol

from src.modules.runtime_data.application.models import (
    FetchPlan,
    FilterExpression,
    FilterSpec,
    PageSpec,
    RuntimeRowsPage,
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

    async def update_where(
        self,
        *,
        descriptor: RuntimeObjectDescriptor,
        filters: Sequence[FilterExpression],
        patch: Mapping[str, Any],
    ) -> list[Mapping[str, Any]]:
        """Обновляет строки по фильтрам и возвращает измененные записи."""
        ...

    async def claim(
        self,
        *,
        descriptor: RuntimeObjectDescriptor,
        filters: Sequence[FilterExpression],
        patch: Mapping[str, Any],
        sorting: Sequence[SortSpec] = (),
        limit: int = 1,
    ) -> list[Mapping[str, Any]]:
        """Атомарно выбирает строки FOR UPDATE SKIP LOCKED, обновляет и возвращает их."""
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

    async def search(
        self,
        *,
        descriptor: RuntimeObjectDescriptor,
        filters: Sequence[FilterExpression] = (),
        sorting: Sequence[SortSpec] = (),
        page: PageSpec,
        fetch_plan: FetchPlan | None = None,
    ) -> RuntimeRowsPage:
        """Возвращает страницу runtime-записей и total count по тем же фильтрам."""
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


class RuntimeRelationCommandGateway(Protocol):
    """Порт команд и точечного чтения runtime relation data."""

    async def get_related_record(
        self,
        *,
        descriptor: RuntimeObjectDescriptor,
        relation_name: str,
        object_id: Any,
    ) -> Mapping[str, Any] | None:
        """Возвращает single related record или None."""
        ...

    async def list_related_records(
        self,
        *,
        descriptor: RuntimeObjectDescriptor,
        relation_name: str,
        object_id: Any,
    ) -> list[Mapping[str, Any]]:
        """Возвращает related records collection."""
        ...

    async def attach_related_record(
        self,
        *,
        descriptor: RuntimeObjectDescriptor,
        relation_name: str,
        object_id: Any,
        related_id: Any,
    ) -> None:
        """Создает M2M связь между двумя records."""
        ...

    async def detach_related_record(
        self,
        *,
        descriptor: RuntimeObjectDescriptor,
        relation_name: str,
        object_id: Any,
        related_id: Any,
    ) -> None:
        """Удаляет M2M связь между двумя records."""
        ...

    async def set_relation(
        self,
        *,
        descriptor: RuntimeObjectDescriptor,
        relation_name: str,
        object_id: Any,
        related_id: Any,
    ) -> None:
        """Устанавливает FK-based relation."""
        ...

    async def unset_relation(
        self,
        *,
        descriptor: RuntimeObjectDescriptor,
        relation_name: str,
        object_id: Any,
        related_id: Any | None = None,
    ) -> None:
        """Сбрасывает FK-based relation."""
        ...
