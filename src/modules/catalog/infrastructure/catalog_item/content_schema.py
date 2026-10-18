from src.modules.catalog.domain.product_type.aggregate import ProductType
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.modules.catalog.domain.product_type.value_object.schema import (
    ProductTypeSchemaSnapshot,
    ContentBlockSnapshot,
)
from src.modules.catalog.domain.error import CatalogNotFoundError
from src.modules.catalog.infrastructure.persistence.models.product_type import (
    ProductTypeModel,
)
from src.modules.catalog.infrastructure.persistence.models.product_type_block import (
    ProductTypeBlockModel,
)
from src.modules.catalog.infrastructure.persistence.models.content_block import (
    ContentBlockModel,
)

from src.modules.catalog.infrastructure.persistence.models.product_type_translation import (
    ProductTypeTranslationModel,
)
from src.modules.catalog.infrastructure.persistence.models.content_block_translation import (
    ContentBlockTranslationModel,
)


class SqlAlchemyProductTypeSchemas:
    """Читает существующие tenant-схемы без создания данных."""

    def __init__(self, session: AsyncSession) -> None:
        """Получает общую tenant session."""
        self._session = session

    async def get_by_code(
        self, code: str = "default", locale: str | None = None
    ) -> ProductTypeSchemaSnapshot:
        """Находит существующую tenant-схему по устойчивому коду."""
        identifier = await self._session.scalar(
            select(ProductTypeModel.id).where(ProductTypeModel.code == code)
        )
        if identifier is None:
            raise CatalogNotFoundError("Схема товара не установлена.")
        return await self.get_by_id(EntityIdVO(identifier), locale)

    async def get_by_id(
        self, identifier: EntityIdVO, locale: str | None = None
    ) -> ProductTypeSchemaSnapshot:
        """Возвращает Default и упорядоченные определения полей."""
        row = (
            await self._session.execute(
                select(ProductTypeModel.code, ProductTypeModel.schema_version).where(
                    ProductTypeModel.id == identifier.uuid
                )
            )
        ).one_or_none()
        if row is None:
            raise CatalogNotFoundError("Системная схема Default не установлена.")
        rows = (
            await self._session.execute(
                select(
                    ContentBlockModel.id,
                    ContentBlockModel.code,
                    ContentBlockModel.value_type,
                    ProductTypeBlockModel.required,
                    ProductTypeBlockModel.position,
                    ContentBlockTranslationModel.label,
                )
                .join(
                    ProductTypeBlockModel,
                    ProductTypeBlockModel.block_id == ContentBlockModel.id,
                )
                .outerjoin(
                    ContentBlockTranslationModel,
                    (
                        ContentBlockTranslationModel.content_block_id
                        == ContentBlockModel.id
                    )
                    & (ContentBlockTranslationModel.locale == locale),
                )
                .where(ProductTypeBlockModel.product_type_id == identifier.uuid)
                .order_by(ProductTypeBlockModel.position)
            )
        ).all()
        label = (
            (
                await self._session.scalar(
                    select(ProductTypeTranslationModel.label).where(
                        ProductTypeTranslationModel.product_type_id == identifier.uuid,
                        ProductTypeTranslationModel.locale == locale,
                    )
                )
            )
            if locale is not None
            else None
        )
        schema = ProductTypeSchemaSnapshot(
            identifier,
            row.code,
            row.schema_version,
            tuple(
                ContentBlockSnapshot(
                    EntityIdVO(r.id),
                    r.code,
                    r.value_type,
                    r.required,
                    r.position,
                    r.label,
                )
                for r in rows
            ),
            label,
        )
        if schema.code == "default":
            ProductType.validate_default_schema(schema)
        return schema
