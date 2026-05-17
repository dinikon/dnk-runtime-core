from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import Any, List
from uuid import UUID

from src.modules.inventory.application.product.dto import ProductDTO
from src.modules.inventory.application.product.query.repository import (
    ProductQueryRepositoryProtocol,
)
from src.modules.inventory.domain.category.value_object import CategoryIdVO
from src.modules.inventory.domain.product.entity import ProductEntity
from src.modules.inventory.domain.product.error import ProductNotFoundError
from src.modules.inventory.domain.product.repository import (
    ProductCommandRepositoryProtocol,
)
from src.modules.inventory.domain.product.value_object import (
    ProductIdVO,
    ProductNameVO,
    SkuVO,
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


class ProductRuntimeRepository(
    ProductCommandRepositoryProtocol,
    ProductQueryRepositoryProtocol,
):
    """Inventory repository товаров поверх runtime_data gateway."""

    _OBJECT_NAME = "product"

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
        product_id: ProductIdVO,
    ) -> ProductEntity | None:
        """Загружает доменную entity товара из runtime-таблицы tenant."""
        descriptor = await self._resolve_descriptor(tenant_id)
        row = await self._runtime_query_gateway.get_by_id(
            descriptor=descriptor,
            object_id=product_id.uuid,
        )
        if row is None:
            return None
        return self._row_to_entity(row)

    async def save(
        self,
        *,
        tenant_id: EntityIdVO,
        product: ProductEntity,
    ) -> ProductEntity:
        """Создает или обновляет runtime-строку товара и возвращает entity."""
        descriptor = await self._resolve_descriptor(tenant_id)
        existing = await self._runtime_query_gateway.get_by_id(
            descriptor=descriptor,
            object_id=product.id.uuid,
        )
        payload = {
            "sku": product.sku.value,
            "product_name": product.product_name.value,
            "description": product.description,
            "category_id": (
                None if product.category_id is None else product.category_id.uuid
            ),
        }

        if existing is None:
            row = await self._runtime_command_gateway.insert(
                descriptor=descriptor,
                payload={
                    "id": product.id.uuid,
                    **payload,
                },
            )
        else:
            row = await self._runtime_command_gateway.update(
                descriptor=descriptor,
                object_id=product.id.uuid,
                patch=payload,
            )
            if row is None:
                raise ProductNotFoundError(str(product.id))

        return self._row_to_entity(row)

    async def delete(
        self,
        *,
        tenant_id: EntityIdVO,
        product_id: ProductIdVO,
    ) -> None:
        """Удаляет runtime-строку товара или поднимает not-found ошибку."""
        descriptor = await self._resolve_descriptor(tenant_id)
        deleted = await self._runtime_command_gateway.delete(
            descriptor=descriptor,
            object_id=product_id.uuid,
        )
        if not deleted:
            raise ProductNotFoundError(str(product_id))

    async def get_by_id(
        self,
        *,
        tenant_id: EntityIdVO,
        product_id: ProductIdVO,
    ) -> ProductDTO | None:
        """Возвращает ProductDTO по id для query-сценариев."""
        descriptor = await self._resolve_descriptor(tenant_id)
        row = await self._runtime_query_gateway.get_by_id(
            descriptor=descriptor,
            object_id=product_id.uuid,
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
        category_id: CategoryIdVO | None = None,
    ) -> List[ProductDTO]:
        """Возвращает страницу ProductDTO, опционально фильтруя по категории."""
        descriptor = await self._resolve_descriptor(tenant_id)
        filters = (
            ()
            if category_id is None
            else (
                self._filter_builder.condition(
                    descriptor=descriptor,
                    field="category_id",
                    op="eq",
                    value=category_id.uuid,
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
        """Получает runtime descriptor inventory-объекта product для tenant."""
        return await self._runtime_object_resolver.resolve(
            tenant_id=tenant_id,
            object_name=self._OBJECT_NAME,
        )

    @staticmethod
    def _row_to_entity(row: Mapping[str, Any]) -> ProductEntity:
        """Мапит runtime row в доменную ProductEntity с проверкой типов."""
        category_id = ProductRuntimeRepository._as_optional_uuid(row.get("category_id"))
        return ProductEntity(
            id=ProductIdVO.from_value(ProductRuntimeRepository._as_uuid(row.get("id"))),
            created_at=ProductRuntimeRepository._as_datetime(row.get("created_at")),
            updated_at=ProductRuntimeRepository._as_datetime(row.get("updated_at")),
            sku=SkuVO(ProductRuntimeRepository._as_str(row.get("sku"))),
            product_name=ProductNameVO(
                ProductRuntimeRepository._as_str(row.get("product_name"))
            ),
            description=ProductRuntimeRepository._as_optional_str(
                row.get("description")
            ),
            category_id=(
                None if category_id is None else CategoryIdVO.from_value(category_id)
            ),
        )

    @staticmethod
    def _row_to_dto(row: Mapping[str, Any]) -> ProductDTO:
        """Мапит runtime row в ProductDTO с проверкой типов."""
        return ProductDTO(
            id=ProductRuntimeRepository._as_uuid(row.get("id")),
            created_at=ProductRuntimeRepository._as_datetime(row.get("created_at")),
            updated_at=ProductRuntimeRepository._as_datetime(row.get("updated_at")),
            sku=ProductRuntimeRepository._as_str(row.get("sku")),
            product_name=ProductRuntimeRepository._as_str(row.get("product_name")),
            description=ProductRuntimeRepository._as_optional_str(
                row.get("description")
            ),
            category_id=ProductRuntimeRepository._as_optional_uuid(
                row.get("category_id")
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
        return ProductRuntimeRepository._as_uuid(value)

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

    @staticmethod
    def _as_optional_str(value: Any) -> str | None:
        """Достает optional строку из runtime row."""
        if value is None:
            return None
        if isinstance(value, str):
            return value
        raise TypeError("Runtime row must contain optional string value.")
