from src.modules.catalog.infrastructure.product_type.persistence.product_type_translations import (
    read_product_type_translations,
    save_product_type_translations,
)
from sqlalchemy import select, insert, update, delete, exists
from sqlalchemy.ext.asyncio import AsyncSession
from src.modules.catalog.domain.product_type.aggregate import ProductType
from src.modules.catalog.domain.product_type.value_object.identifier import (
    ProductTypeIdVO,
)
from src.modules.catalog.domain.product_type.error import ProductTypeNotFoundError
from src.modules.catalog.infrastructure.product_type.persistence.mapper import (
    ProductTypeMapper,
)
from src.modules.catalog.infrastructure.persistence.models.product_type import (
    ProductTypeModel,
)
from src.modules.catalog.infrastructure.persistence.models.product import ProductModel
from src.modules.catalog.infrastructure.persistence.models.product_type_block import (
    ProductTypeBlockModel,
)


class SqlAlchemyProductTypeRepository:
    """Хранит агрегат на сессии общего tenant UoW; commit остаётся снаружи."""

    def __init__(self, session: AsyncSession) -> None:
        """Получает сессию с уже привязанной tenant-схемой."""
        self._session = session

    async def get(self, identifier: ProductTypeIdVO) -> ProductType:
        """Читает сохранённые части и восстанавливает агрегат через mapper."""
        result = await self._session.execute(
            select(ProductTypeModel.__table__).where(
                ProductTypeModel.id == identifier.uuid
            )
        )
        row = result.mappings().one_or_none()
        if row is None:
            raise ProductTypeNotFoundError("Объект отсутствует.")
        child = await self._session.execute(
            select(ProductTypeBlockModel.__table__)
            .where(ProductTypeBlockModel.product_type_id == identifier.uuid)
            .order_by(ProductTypeBlockModel.scope, ProductTypeBlockModel.position)
        )
        links = child.mappings().all()
        return ProductTypeMapper.to_domain(
            row,
            links,
            translations=await read_product_type_translations(
                self._session, identifier.uuid
            ),
        )

    async def add(self, entity: ProductType) -> None:
        """Добавляет все принадлежащие агрегату части без commit."""
        await self._session.execute(
            insert(ProductTypeModel).values(ProductTypeMapper.to_insert_values(entity))
        )
        if entity.blocks:
            await self._session.execute(
                insert(ProductTypeBlockModel), ProductTypeMapper.link_values(entity)
            )
        await save_product_type_translations(
            self._session, entity.id.uuid, entity.translations
        )

    async def save(self, entity: ProductType) -> None:
        """Сохраняет доменное состояние в текущей общей транзакции."""
        await self._session.execute(
            update(ProductTypeModel)
            .where(ProductTypeModel.id == entity.id.uuid)
            .values(ProductTypeMapper.to_update_values(entity))
        )
        await self._session.execute(
            delete(ProductTypeBlockModel).where(
                ProductTypeBlockModel.product_type_id == entity.id.uuid
            )
        )
        if entity.blocks:
            await self._session.execute(
                insert(ProductTypeBlockModel), ProductTypeMapper.link_values(entity)
            )
        await save_product_type_translations(
            self._session, entity.id.uuid, entity.translations
        )

    async def delete(self, entity: ProductType) -> None:
        """Удаляет агрегат после проверок Domain, без commit."""
        await self._session.execute(
            delete(ProductTypeModel).where(ProductTypeModel.id == entity.id.uuid)
        )

    async def is_used(self, identifier: ProductTypeIdVO) -> bool:
        """Проверяет ссылки товаров без восстановления read-проекций."""
        return bool(
            await self._session.scalar(
                select(exists().where(ProductModel.product_type_id == identifier.uuid))
            )
        )

    async def get_default_id(self) -> ProductTypeIdVO:
        """Читает ID системного типа, созданного миграцией tenant."""
        identifier = await self._session.scalar(
            select(ProductTypeModel.id).where(
                ProductTypeModel.code == "default", ProductTypeModel.is_system.is_(True)
            )
        )
        if identifier is None:
            raise ProductTypeNotFoundError(
                "Системный Default отсутствует. Проверьте tenant-миграции."
            )
        return ProductTypeIdVO(identifier)
