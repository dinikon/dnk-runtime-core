from src.modules.catalog.infrastructure.persistence.models.content_block import (
    ContentBlockModel,
)
from src.modules.catalog.infrastructure.persistence.models.catalog_item_translation import (
    CatalogItemTranslationModel,
)
from src.modules.catalog.infrastructure.persistence.models.catalog_item_content_value import (
    CatalogItemContentValueModel,
)
from src.modules.catalog.infrastructure.persistence.models.catalog_item_gallery import (
    CatalogItemGalleryModel,
)
from src.modules.catalog.infrastructure.persistence.models.catalog_item_image import (
    CatalogItemImageModel,
)
from typing import Any
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

PART_MODELS = (
    CatalogItemTranslationModel,
    CatalogItemContentValueModel,
    CatalogItemGalleryModel,
    CatalogItemImageModel,
)


async def read_parts(
    session: AsyncSession, identifiers: tuple[UUID, ...], locale: str | None = None
) -> dict[str, list[dict[str, Any]]]:
    """Читает табличные части одним batch на вид связи, без запросов на каждый item."""
    parts: dict[str, list[dict[str, Any]]] = {}
    for model in PART_MODELS:
        table = model.__table__
        if not identifiers:
            parts[table.name] = []
            continue
        statement = select(table).where(table.c.catalog_item_id.in_(identifiers))
        if model is CatalogItemContentValueModel:
            statement = (
                select(table, ContentBlockModel.code.label("block_code"))
                .join(ContentBlockModel, ContentBlockModel.id == table.c.block_id)
                .where(table.c.catalog_item_id.in_(identifiers))
            )
        if locale is not None and "locale" in table.c:
            statement = statement.where(table.c.locale == locale)
        rows = (await session.execute(statement)).mappings().all()
        parts[table.name] = [dict(r) for r in rows]
    return parts
