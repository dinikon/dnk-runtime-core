from sqlalchemy import insert, select
from sqlalchemy.ext.asyncio import AsyncSession
from src.modules.catalog.domain.product_type.aggregate import ProductType
from src.modules.catalog.infrastructure.product_type.persistence.mapper import (
    ProductTypeMapper,
)
from src.modules.catalog.infrastructure.persistence.models.product_type import (
    ProductTypeModel,
)
from src.modules.catalog.infrastructure.persistence.models.product_type_block import (
    ProductTypeBlockModel,
)
from src.modules.catalog.infrastructure.persistence.models.product_type_translation import (
    ProductTypeTranslationModel,
)
from src.modules.catalog.infrastructure.persistence.models.content_block import (
    ContentBlockModel,
)
from src.modules.catalog.infrastructure.persistence.models.content_block_translation import (
    ContentBlockTranslationModel,
)


class SqlAlchemyProductTypeRepository:
    """Хранит схему вместе с блоками в общей транзакции создания tenant."""

    def __init__(self, session: AsyncSession) -> None:
        """Принимает уже привязанную tenant-сессию внешнего UoW."""
        self._session = session

    async def get_by_code(self, code: str) -> ProductType | None:
        """Читает полный агрегат для идемпотентной инициализации."""
        row = (
            (
                await self._session.execute(
                    select(ProductTypeModel.__table__).where(
                        ProductTypeModel.code == code
                    )
                )
            )
            .mappings()
            .one_or_none()
        )
        if row is None:
            return None
        blocks = (
            (
                await self._session.execute(
                    select(
                        ContentBlockModel.__table__,
                        ProductTypeBlockModel.required,
                        ProductTypeBlockModel.position,
                    )
                    .join(
                        ProductTypeBlockModel,
                        ProductTypeBlockModel.block_id == ContentBlockModel.id,
                    )
                    .where(ProductTypeBlockModel.product_type_id == row["id"])
                    .order_by(ProductTypeBlockModel.position)
                )
            )
            .mappings()
            .all()
        )
        labels = (
            (
                await self._session.execute(
                    select(ProductTypeTranslationModel.__table__).where(
                        ProductTypeTranslationModel.product_type_id == row["id"]
                    )
                )
            )
            .mappings()
            .all()
        )
        block_labels = (
            (
                await self._session.execute(
                    select(ContentBlockTranslationModel.__table__).where(
                        ContentBlockTranslationModel.content_block_id.in_(
                            [block["id"] for block in blocks]
                        )
                    )
                )
            )
            .mappings()
            .all()
        )
        return ProductTypeMapper.to_domain(row, blocks, labels, block_labels)

    async def add(self, product_type: ProductType) -> None:
        """Записывает все части схемы без самостоятельного commit."""
        audit = ProductTypeMapper.audit(product_type)
        await self._session.execute(
            insert(ProductTypeModel).values(
                id=product_type.id.uuid,
                code=product_type.code,
                schema_version=product_type.schema_version,
                is_system=product_type.is_system,
                **audit,
            )
        )
        await self._session.execute(
            insert(ContentBlockModel),
            [
                dict(
                    id=block.id.uuid,
                    code=block.code,
                    value_type=block.value_type,
                    is_system=product_type.is_system,
                    **audit,
                )
                for block in product_type.blocks
            ],
        )
        await self._session.execute(
            insert(ProductTypeBlockModel),
            [
                dict(
                    product_type_id=product_type.id.uuid,
                    block_id=block.id.uuid,
                    required=block.required,
                    position=block.position,
                )
                for block in product_type.blocks
            ],
        )
        labels = [
            dict(product_type_id=product_type.id.uuid, locale=locale, label=label)
            for locale, label in product_type.labels.items()
        ]
        if labels:
            await self._session.execute(insert(ProductTypeTranslationModel), labels)
        block_labels = [
            dict(content_block_id=block.id.uuid, locale=locale, label=label)
            for block in product_type.blocks
            for locale, label in block.labels.items()
        ]
        if block_labels:
            await self._session.execute(
                insert(ContentBlockTranslationModel), block_labels
            )
