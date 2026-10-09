from src.modules.catalog.infrastructure.product.persistence.variant_translations import (
    read_variant_translations,
    save_variant_translations,
)
from src.modules.catalog.infrastructure.product.persistence.product_translations import (
    read_product_translations,
    save_product_translations,
)
from sqlalchemy import select, insert, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from src.modules.catalog.domain.product.aggregate import Product
from src.modules.catalog.domain.product.value_object.identifier import ProductIdVO
from src.modules.catalog.domain.product.error import ProductNotFoundError
from src.modules.catalog.domain.product_type.value_object.identifier import (
    ProductTypeIdVO,
)
from src.modules.catalog.infrastructure.product.persistence.mapper import ProductMapper
from src.modules.catalog.infrastructure.persistence.models.product import ProductModel
from src.modules.catalog.infrastructure.persistence.models.variant import VariantModel


class SqlAlchemyProductRepository:
    """Хранит агрегат на сессии общего tenant UoW; commit остаётся снаружи."""

    def __init__(self, session: AsyncSession) -> None:
        """Получает сессию с уже привязанной tenant-схемой."""
        self._session = session

    async def get(self, identifier: ProductIdVO) -> Product:
        """Читает сохранённые части и восстанавливает агрегат через mapper."""
        result = await self._session.execute(
            select(ProductModel.__table__).where(ProductModel.id == identifier.uuid)
        )
        row = result.mappings().one_or_none()
        if row is None:
            raise ProductNotFoundError("Объект отсутствует.")
        child = await self._session.execute(
            select(VariantModel.__table__).where(
                VariantModel.product_id == identifier.uuid
            )
        )
        variant = child.mappings().one()
        return ProductMapper.to_domain(
            row,
            {
                **variant,
                "translations": await read_variant_translations(
                    self._session, variant["id"]
                ),
            },
            translations=await read_product_translations(
                self._session, identifier.uuid
            ),
        )

    async def add(self, entity: Product) -> None:
        """Добавляет все принадлежащие агрегату части без commit."""
        await self._session.execute(
            insert(ProductModel).values(ProductMapper.to_insert_values(entity))
        )
        await self._session.execute(
            insert(VariantModel).values(ProductMapper.variant_values(entity))
        )
        await save_product_translations(
            self._session, entity.id.uuid, entity.translations
        )
        await save_variant_translations(
            self._session, entity.variant.id.uuid, entity.variant.translations
        )

    async def save(self, entity: Product) -> None:
        """Сохраняет доменное состояние в текущей общей транзакции."""
        await self._session.execute(
            update(ProductModel)
            .where(ProductModel.id == entity.id.uuid)
            .values(ProductMapper.to_update_values(entity))
        )
        await self._session.execute(
            update(VariantModel)
            .where(VariantModel.product_id == entity.id.uuid)
            .values(ProductMapper.variant_values(entity))
        )
        await save_product_translations(
            self._session, entity.id.uuid, entity.translations
        )
        await save_variant_translations(
            self._session, entity.variant.id.uuid, entity.variant.translations
        )

    async def delete(self, entity: Product) -> None:
        """Удаляет агрегат после проверок Domain, без commit."""
        await self._session.execute(
            delete(ProductModel).where(ProductModel.id == entity.id.uuid)
        )

    async def get_by_type(self, identifier: ProductTypeIdVO) -> tuple[Product, ...]:
        """Загружает владельцев контента для проверки новой схемы в write-сценарии."""
        ids = (
            (
                await self._session.execute(
                    select(ProductModel.id).where(
                        ProductModel.product_type_id == identifier.uuid
                    )
                )
            )
            .scalars()
            .all()
        )
        return tuple([await self.get(ProductIdVO(i)) for i in ids])
