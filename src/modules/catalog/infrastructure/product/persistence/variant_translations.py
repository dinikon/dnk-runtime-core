from uuid import UUID
from sqlalchemy import select, insert, delete
from sqlalchemy.ext.asyncio import AsyncSession
from src.modules.catalog.infrastructure.persistence.models.variant_translation import (
    VariantTranslationModel,
)
from src.modules.catalog.infrastructure.persistence.models.variant_content_value import (
    VariantContentValueModel,
)


async def read_variant_translations(
    session: AsyncSession, identifier: UUID
) -> dict[str, dict[str, str]]:
    """Читает табличные части variant для write restoration либо read projection."""
    rows = (
        (
            await session.execute(
                select(VariantTranslationModel.__table__).where(
                    VariantTranslationModel.variant_id == identifier
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
                select(VariantContentValueModel.__table__).where(
                    VariantContentValueModel.variant_id == identifier
                )
            )
        )
        .mappings()
        .all()
    )
    for row in values:
        translations[row["locale"]][str(row["block_id"])] = row["value"]
    return translations


async def save_variant_translations(
    session: AsyncSession, identifier: UUID, translations: dict[str, dict[str, str]]
) -> None:
    """Заменяет принадлежащие агрегату переводы без commit и бизнес-валидации."""
    await session.execute(
        delete(VariantTranslationModel).where(
            VariantTranslationModel.variant_id == identifier
        )
    )
    if translations:
        await session.execute(
            insert(VariantTranslationModel),
            [{"variant_id": identifier, "locale": locale} for locale in translations],
        )
    values = [
        {
            "variant_id": identifier,
            "locale": locale,
            "block_id": UUID(block),
            "value": value,
        }
        for locale, blocks in translations.items()
        for block, value in blocks.items()
    ]
    if values:
        await session.execute(insert(VariantContentValueModel), values)
