from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.modules.catalog.domain.product_type.value_object.schema import (
    ProductTypeSchemaSnapshot,
    ContentBlockSnapshot,
    DEFAULT_TYPE_ID,
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


class SqlAlchemyDefaultContentSchema:
    """Читает фиксированную схему; изменяемого API типов нет."""

    def __init__(self, session: AsyncSession) -> None:
        """Получает общую tenant session."""
        self._session = session

    async def get_default(self, locale: str | None = None) -> ProductTypeSchemaSnapshot:
        """Возвращает Default и упорядоченные определения полей."""
        version = await self._session.scalar(
            select(ProductTypeModel.schema_version).where(
                ProductTypeModel.id == DEFAULT_TYPE_ID.uuid
            )
        )
        if version is None:
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
                .where(ProductTypeBlockModel.product_type_id == DEFAULT_TYPE_ID.uuid)
                .order_by(ProductTypeBlockModel.position)
            )
        ).all()
        label = (
            (
                await self._session.scalar(
                    select(ProductTypeTranslationModel.label).where(
                        ProductTypeTranslationModel.product_type_id
                        == DEFAULT_TYPE_ID.uuid,
                        ProductTypeTranslationModel.locale == locale,
                    )
                )
            )
            if locale is not None
            else None
        )
        return ProductTypeSchemaSnapshot(
            DEFAULT_TYPE_ID,
            "default",
            version,
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
