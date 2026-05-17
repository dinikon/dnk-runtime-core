from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import Any, List
from uuid import UUID

from src.modules.inventory.application.category.dto import CategoryDTO
from src.modules.inventory.application.category.query.repository import (
    CategoryQueryRepositoryProtocol,
)
from src.modules.inventory.domain.category.entity import CategoryEntity
from src.modules.inventory.domain.category.error import CategoryNotFoundError
from src.modules.inventory.domain.category.repository import (
    CategoryCommandRepositoryProtocol,
)
from src.modules.inventory.domain.category.value_object import (
    CategoryIdVO,
    CategoryNameVO,
)
from src.modules.runtime_data.application.models import PageSpec, SortSpec
from src.modules.runtime_data.application.ports import (
    RuntimeCommandGateway,
    RuntimeQueryGateway,
)
from src.modules.runtime_data.application.query.typed_filter_builder import (
    RuntimeTypedFilterBuilder,
)
from src.modules.schema_registry.runtime import RuntimeObjectResolverProtocol
from src.modules.shared import EntityIdVO


class CategoryRuntimeRepository(
    CategoryCommandRepositoryProtocol,
    CategoryQueryRepositoryProtocol,
):
    """Inventory repository категорий поверх runtime_data gateway."""

    _OBJECT_NAME = "product_category"

    def __init__(
        self,
        runtime_object_resolver: RuntimeObjectResolverProtocol,
        runtime_command_gateway: RuntimeCommandGateway,
        runtime_query_gateway: RuntimeQueryGateway,
    ) -> None:
        """Инициализирует repository resolver-ом descriptor и runtime gateways."""
        self._runtime_object_resolver = runtime_object_resolver
        self._runtime_command_gateway = runtime_command_gateway
        self._runtime_query_gateway = runtime_query_gateway
        self._filter_builder = RuntimeTypedFilterBuilder()

    async def load(
        self,
        *,
        tenant_id: EntityIdVO,
        category_id: CategoryIdVO,
    ) -> CategoryEntity | None:
        """Загружает доменную entity категории из runtime-таблицы tenant."""
        descriptor = await self._resolve_descriptor(tenant_id)
        row = await self._runtime_query_gateway.get_by_id(
            descriptor=descriptor,
            object_id=category_id.uuid,
        )
        if row is None:
            return None
        return self._row_to_entity(row)

    async def save(
        self,
        *,
        tenant_id: EntityIdVO,
        category: CategoryEntity,
    ) -> CategoryEntity:
        """Создает или обновляет runtime-строку категории и возвращает entity."""
        descriptor = await self._resolve_descriptor(tenant_id)
        existing = await self._runtime_query_gateway.get_by_id(
            descriptor=descriptor,
            object_id=category.id.uuid,
        )
        payload = {
            "name": category.name.value,
            "parent_category_id": (
                None
                if category.parent_category_id is None
                else category.parent_category_id.uuid
            ),
        }

        if existing is None:
            row = await self._runtime_command_gateway.insert(
                descriptor=descriptor,
                payload={
                    "id": category.id.uuid,
                    **payload,
                },
            )
        else:
            row = await self._runtime_command_gateway.update(
                descriptor=descriptor,
                object_id=category.id.uuid,
                patch=payload,
            )
            if row is None:
                raise CategoryNotFoundError(str(category.id))

        return self._row_to_entity(row)

    async def delete(
        self,
        *,
        tenant_id: EntityIdVO,
        category_id: CategoryIdVO,
    ) -> None:
        """Удаляет runtime-строку категории или поднимает not-found ошибку."""
        descriptor = await self._resolve_descriptor(tenant_id)
        deleted = await self._runtime_command_gateway.delete(
            descriptor=descriptor,
            object_id=category_id.uuid,
        )
        if not deleted:
            raise CategoryNotFoundError(str(category_id))

    async def get_by_id(
        self,
        *,
        tenant_id: EntityIdVO,
        category_id: CategoryIdVO,
    ) -> CategoryDTO | None:
        """Возвращает CategoryDTO по id для query-сценариев."""
        descriptor = await self._resolve_descriptor(tenant_id)
        row = await self._runtime_query_gateway.get_by_id(
            descriptor=descriptor,
            object_id=category_id.uuid,
        )
        if row is None:
            return None
        return self._row_to_dto(row)

    async def list(
        self,
        *,
        tenant_id: EntityIdVO,
        limit: int,
        offset: int,
        parent_category_id: CategoryIdVO | None = None,
    ) -> List[CategoryDTO]:
        """Возвращает страницу CategoryDTO, опционально фильтруя по parent."""
        descriptor = await self._resolve_descriptor(tenant_id)
        filters = (
            ()
            if parent_category_id is None
            else (
                self._filter_builder.condition(
                    descriptor=descriptor,
                    field="parent_category_id",
                    op="eq",
                    value=parent_category_id.uuid,
                ),
            )
        )
        rows = await self._runtime_query_gateway.list(
            descriptor=descriptor,
            filters=filters,
            sorting=(
                SortSpec(field="created_at", direction="asc"),
                SortSpec(field="id", direction="asc"),
            ),
            page=PageSpec(limit=limit, offset=offset),
        )
        return [self._row_to_dto(row) for row in rows]

    async def _resolve_descriptor(self, tenant_id: EntityIdVO):
        """Получает runtime descriptor inventory-объекта product_category."""
        return await self._runtime_object_resolver.resolve(
            tenant_id=tenant_id,
            object_name=self._OBJECT_NAME,
        )

    @staticmethod
    def _row_to_entity(row: Mapping[str, Any]) -> CategoryEntity:
        """Мапит runtime row в доменную CategoryEntity с проверкой типов."""
        parent_category_id = CategoryRuntimeRepository._as_optional_uuid(
            row.get("parent_category_id")
        )
        return CategoryEntity(
            id=CategoryIdVO.from_value(
                CategoryRuntimeRepository._as_uuid(row.get("id"))
            ),
            created_at=CategoryRuntimeRepository._as_datetime(row.get("created_at")),
            updated_at=CategoryRuntimeRepository._as_datetime(row.get("updated_at")),
            name=CategoryNameVO(CategoryRuntimeRepository._as_str(row.get("name"))),
            parent_category_id=(
                None
                if parent_category_id is None
                else CategoryIdVO.from_value(parent_category_id)
            ),
        )

    @staticmethod
    def _row_to_dto(row: Mapping[str, Any]) -> CategoryDTO:
        """Мапит runtime row в CategoryDTO с проверкой типов."""
        return CategoryDTO(
            id=CategoryRuntimeRepository._as_uuid(row.get("id")),
            created_at=CategoryRuntimeRepository._as_datetime(row.get("created_at")),
            updated_at=CategoryRuntimeRepository._as_datetime(row.get("updated_at")),
            name=CategoryRuntimeRepository._as_str(row.get("name")),
            parent_category_id=CategoryRuntimeRepository._as_optional_uuid(
                row.get("parent_category_id")
            ),
        )

    @staticmethod
    def _as_uuid(value: Any) -> UUID:
        """Достает UUID из runtime row или поднимает TypeError."""
        if isinstance(value, UUID):
            return value
        if isinstance(value, str):
            return UUID(value)
        raise TypeError("Runtime row must contain UUID value.")

    @staticmethod
    def _as_optional_uuid(value: Any) -> UUID | None:
        """Достает optional UUID из runtime row."""
        if value is None:
            return None
        return CategoryRuntimeRepository._as_uuid(value)

    @staticmethod
    def _as_datetime(value: Any) -> datetime:
        """Достает datetime из runtime row или поднимает TypeError."""
        if isinstance(value, datetime):
            return value
        raise TypeError("Runtime row must contain datetime value.")

    @staticmethod
    def _as_str(value: Any) -> str:
        """Достает обязательную строку из runtime row."""
        if isinstance(value, str):
            return value
        raise TypeError("Runtime row must contain string value.")
