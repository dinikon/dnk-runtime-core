from uuid import UUID
from sqlalchemy import select, insert, delete
from sqlalchemy.ext.asyncio import AsyncSession
from src.modules.catalog.infrastructure.persistence.models.product_translation import (
    ProductTranslationModel,
)
from src.modules.catalog.infrastructure.persistence.models.product_content_value import (
    ProductContentValueModel,
)


async def read_product_translations(
    session: AsyncSession, identifier: UUID
) -> dict[str, dict[str, str]]:
    """Читает табличные части product для write restoration либо read projection."""
    rows = (
        (
            await session.execute(
                select(ProductTranslationModel.__table__).where(
                    ProductTranslationModel.product_id == identifier
                )
            )
        )
        .mappings()
        .all()
    )
    translations = {r["locale"]: {} for r in rows}
    values = (
        (
            await session.execute(
                select(ProductContentValueModel.__table__).where(
                    ProductContentValueModel.product_id == identifier
                )
            )
        )
        .mappings()
        .all()
    )
    for row in values:
        translations[row["locale"]][str(row["block_id"])] = row["value"]
    return translations


async def save_product_translations(
    session: AsyncSession, identifier: UUID, translations: dict[str, dict[str, str]]
) -> None:
    """Заменяет принадлежащие агрегату переводы без commit и бизнес-валидации."""
    await session.execute(
        delete(ProductTranslationModel).where(
            ProductTranslationModel.product_id == identifier
        )
    )
    if translations:
        await session.execute(
            insert(ProductTranslationModel),
            [{"product_id": identifier, "locale": locale} for locale in translations],
        )
    values = [
        {
            "product_id": identifier,
            "locale": locale,
            "block_id": UUID(block),
            "value": value,
        }
        for locale, blocks in translations.items()
        for block, value in blocks.items()
    ]
    if values:
        await session.execute(insert(ProductContentValueModel), values)
