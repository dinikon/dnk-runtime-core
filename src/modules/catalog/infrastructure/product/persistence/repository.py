from src.modules.catalog.infrastructure.persistence.models.product_attribute_value import (
    ProductAttributeValueModel,
)
from src.modules.catalog.infrastructure.persistence.models.product_category import (
    ProductCategoryModel,
)
from src.modules.catalog.infrastructure.persistence.models.product_tag import (
    ProductTagModel,
)
from sqlalchemy import select, insert, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from src.modules.catalog.domain.product.aggregate import Product
from src.modules.catalog.domain.product.entity.structure import VariableProductStructure
from src.modules.catalog.domain.product.value_object.identifier import ProductIdVO
from src.modules.catalog.domain.product_type.value_object.identifier import (
    ProductTypeIdVO,
)
from src.modules.catalog.domain.product.error import ProductNotFoundError
from src.modules.catalog.infrastructure.product.persistence.mapper import ProductMapper
from src.modules.catalog.infrastructure.product.persistence.structure_rows import (
    read_product_structure,
)
from src.modules.catalog.infrastructure.product.persistence.product_translations import (
    read_product_translations,
    save_product_translations,
)
from src.modules.catalog.infrastructure.product.persistence.variant_translations import (
    save_variant_translations,
)
from src.modules.catalog.infrastructure.persistence.models.product import ProductModel
from src.modules.catalog.infrastructure.persistence.models.variant import VariantModel
from src.modules.catalog.infrastructure.persistence.models.product_axis import (
    ProductAxisModel,
)
from src.modules.catalog.infrastructure.persistence.models.product_axis_option import (
    ProductAxisOptionModel,
)
from src.modules.catalog.infrastructure.persistence.models.variant_selection import (
    VariantSelectionModel,
)
from src.modules.catalog.infrastructure.persistence.models.product_default_selection import (
    ProductDefaultSelectionModel,
)


class SqlAlchemyProductRepository:
    """Хранит Product со всеми позициями на общей tenant-сессии внешнего UoW."""

    def __init__(self, session: AsyncSession) -> None:
        """Получает сессию без управления tenant или commit."""
        self._session = session

    async def get(self, identifier: ProductIdVO) -> Product:
        """Читает собственные части агрегата и восстанавливает через mapper."""
        row = (
            (
                await self._session.execute(
                    select(ProductModel.__table__).where(
                        ProductModel.id == identifier.uuid
                    )
                )
            )
            .mappings()
            .one_or_none()
        )
        if row is None:
            raise ProductNotFoundError("Объект отсутствует.")
        return ProductMapper.to_domain(
            row,
            await read_product_structure(self._session, identifier.uuid),
            await read_product_translations(self._session, identifier.uuid),
        )

    async def add(self, entity: Product) -> None:
        """Добавляет корень и все принадлежащие строки без commit."""
        await self._session.execute(
            insert(ProductModel).values(ProductMapper.to_insert_values(entity))
        )
        await self._save_parts(entity)

    async def save(self, entity: Product) -> None:
        """Сохраняет доменное состояние целиком, сохраняя ID оставленных позиций."""
        await self._session.execute(
            update(ProductModel)
            .where(ProductModel.id == entity.id.uuid)
            .values(ProductMapper.to_update_values(entity))
        )
        await self._save_parts(entity)

    async def _save_parts(self, entity: Product) -> None:
        """Синхронизирует структуру в порядке FK внутри общей транзакции."""
        await self._session.execute(
            delete(VariantSelectionModel).where(
                VariantSelectionModel.product_id == entity.id.uuid
            )
        )
        await self._session.execute(
            delete(ProductDefaultSelectionModel).where(
                ProductDefaultSelectionModel.product_id == entity.id.uuid
            )
        )
        await self._session.execute(
            delete(ProductAxisModel).where(
                ProductAxisModel.product_id == entity.id.uuid
            )
        )
        existing = set(
            (
                await self._session.scalars(
                    select(VariantModel.id).where(
                        VariantModel.product_id == entity.id.uuid
                    )
                )
            ).all()
        )
        removed = existing - {v.id.uuid for v in entity.variants}
        if removed:
            await self._session.execute(
                delete(VariantModel).where(VariantModel.id.in_(removed))
            )
        for variant in entity.variants:
            values = ProductMapper.variant_values(entity.id, variant)
            if variant.id.uuid in existing:
                await self._session.execute(
                    update(VariantModel)
                    .where(VariantModel.id == variant.id.uuid)
                    .values(**values)
                )
            else:
                await self._session.execute(insert(VariantModel).values(**values))
            await save_variant_translations(
                self._session, variant.id.uuid, variant.translations
            )
        if isinstance(entity.structure, VariableProductStructure):
            for axis in entity.structure.axes:
                await self._session.execute(
                    insert(ProductAxisModel).values(
                        product_id=entity.id.uuid,
                        attribute_id=axis.attribute_id.uuid,
                        position=axis.position,
                    )
                )
                await self._session.execute(
                    insert(ProductAxisOptionModel),
                    [
                        {
                            "product_id": entity.id.uuid,
                            "attribute_id": axis.attribute_id.uuid,
                            "option_id": o.uuid,
                        }
                        for o in axis.option_ids
                    ],
                )
            selections = [
                {
                    "product_id": entity.id.uuid,
                    "variant_id": v.id.uuid,
                    "attribute_id": a.uuid,
                    "option_id": o.uuid,
                }
                for v in entity.variants
                for a, o in v.selection.values
            ]
            await self._session.execute(insert(VariantSelectionModel), selections)
            if entity.structure.default_selection is not None:
                await self._session.execute(
                    insert(ProductDefaultSelectionModel),
                    [
                        {
                            "product_id": entity.id.uuid,
                            "attribute_id": a.uuid,
                            "option_id": o.uuid,
                        }
                        for a, o in entity.structure.default_selection.values
                    ],
                )
        for model in (
            ProductAttributeValueModel,
            ProductCategoryModel,
            ProductTagModel,
        ):
            await self._session.execute(
                delete(model).where(model.product_id == entity.id.uuid)
            )
        if entity.attribute_values:
            await self._session.execute(
                insert(ProductAttributeValueModel),
                [
                    {
                        "product_id": entity.id.uuid,
                        "attribute_id": v.attribute_id.uuid,
                        "option_id": v.option_id.uuid,
                        "visible": v.visible,
                        "position": v.position,
                    }
                    for v in entity.attribute_values
                ],
            )
        if entity.category_ids:
            await self._session.execute(
                insert(ProductCategoryModel),
                [
                    {
                        "product_id": entity.id.uuid,
                        "category_id": i.uuid,
                        "is_primary": i == entity.primary_category_id,
                    }
                    for i in entity.category_ids
                ],
            )
        if entity.tag_ids:
            await self._session.execute(
                insert(ProductTagModel),
                [
                    {"product_id": entity.id.uuid, "tag_id": i.uuid}
                    for i in entity.tag_ids
                ],
            )
        await save_product_translations(
            self._session, entity.id.uuid, entity.translations
        )

    async def delete(self, entity: Product) -> None:
        """Удаляет агрегат и его структуру без самостоятельного commit."""
        await self._session.execute(
            delete(VariantSelectionModel).where(
                VariantSelectionModel.product_id == entity.id.uuid
            )
        )
        await self._session.execute(
            delete(ProductDefaultSelectionModel).where(
                ProductDefaultSelectionModel.product_id == entity.id.uuid
            )
        )
        await self._session.execute(
            delete(ProductModel).where(ProductModel.id == entity.id.uuid)
        )

    async def get_by_type(self, identifier: ProductTypeIdVO) -> tuple[Product, ...]:
        """Загружает владельцев всех переводов для проверки изменяемой схемы."""
        ids = (
            await self._session.scalars(
                select(ProductModel.id).where(
                    ProductModel.product_type_id == identifier.uuid
                )
            )
        ).all()
        return tuple([await self.get(ProductIdVO(identifier)) for identifier in ids])
