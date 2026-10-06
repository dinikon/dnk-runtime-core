from sqlalchemy import delete, insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.catalog.domain.product_type.aggregate import ProductType
from src.modules.catalog.domain.product_type.value_object.product_type_id import (
    ProductTypeIdVO,
)
from src.modules.catalog.infrastructure.persistence.models.product_type_content_block import (
    ProductTypeContentBlockModel,
)
from src.modules.catalog.infrastructure.persistence.models.product_type import (
    ProductTypeModel,
)
from src.modules.catalog.infrastructure.persistence.models.product_type_translation import (
    ProductTypeTranslationModel,
)
from src.modules.catalog.infrastructure.product_type.persistence.mapper import (
    ProductTypeMapper,
)


class SqlAlchemyProductTypeRepository:
    """Сохраняет корень ProductType в общей tenant-транзакции."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_for_update(self, type_id: ProductTypeIdVO) -> ProductType | None:
        row = (
            await self._session.execute(
                select(ProductTypeModel)
                .where(ProductTypeModel.id == type_id.uuid)
                .with_for_update()
            )
        ).scalar_one_or_none()
        if row is None:
            return None
        translations = (
            (
                await self._session.execute(
                    select(ProductTypeTranslationModel).where(
                        ProductTypeTranslationModel.product_type_id == type_id.uuid
                    )
                )
            )
            .scalars()
            .all()
        )
        assignments = (
            (
                await self._session.execute(
                    select(ProductTypeContentBlockModel).where(
                        ProductTypeContentBlockModel.product_type_id == type_id.uuid
                    )
                )
            )
            .scalars()
            .all()
        )
        return ProductTypeMapper.to_domain(row, list(translations), list(assignments))

    async def add(self, product_type: ProductType) -> None:
        await self._session.execute(
            insert(ProductTypeModel).values(
                ProductTypeMapper.to_insert_values(product_type)
            )
        )
        await self._write_children(product_type)

    async def save(self, product_type: ProductType) -> None:
        await self._session.execute(
            update(ProductTypeModel)
            .where(ProductTypeModel.id == product_type.id.uuid)
            .values(schema_version=product_type.schema_version)
        )
        await self._session.execute(
            delete(ProductTypeContentBlockModel).where(
                ProductTypeContentBlockModel.product_type_id == product_type.id.uuid
            )
        )
        await self._session.execute(
            delete(ProductTypeTranslationModel).where(
                ProductTypeTranslationModel.product_type_id == product_type.id.uuid
            )
        )
        await self._write_children(product_type)

    async def _write_children(self, product_type: ProductType) -> None:
        await self._session.execute(
            insert(ProductTypeTranslationModel),
            ProductTypeMapper.to_translation_values(product_type),
        )
        assignments = ProductTypeMapper.to_assignment_values(product_type)
        if assignments:
            await self._session.execute(
                insert(ProductTypeContentBlockModel), assignments
            )

    async def delete(self, product_type: ProductType) -> None:
        await self._session.execute(
            delete(ProductTypeModel).where(ProductTypeModel.id == product_type.id.uuid)
        )
