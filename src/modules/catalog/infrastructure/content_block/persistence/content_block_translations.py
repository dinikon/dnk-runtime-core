from uuid import UUID
from sqlalchemy import select, insert, delete
from sqlalchemy.ext.asyncio import AsyncSession
from src.modules.catalog.infrastructure.persistence.models.content_block_translation import (
    ContentBlockTranslationModel,
)


async def read_content_block_translations(
    session: AsyncSession, identifier: UUID
) -> dict[str, str]:
    """Читает табличные части content_block для write restoration либо read projection."""
    rows = (
        (
            await session.execute(
                select(ContentBlockTranslationModel.__table__).where(
                    ContentBlockTranslationModel.content_block_id == identifier
                )
            )
        )
        .mappings()
        .all()
    )
    return {r["locale"]: r["label"] for r in rows}


async def save_content_block_translations(
    session: AsyncSession, identifier: UUID, translations: dict[str, str]
) -> None:
    """Заменяет принадлежащие агрегату переводы без commit и бизнес-валидации."""
    await session.execute(
        delete(ContentBlockTranslationModel).where(
            ContentBlockTranslationModel.content_block_id == identifier
        )
    )
    if translations:
        await session.execute(
            insert(ContentBlockTranslationModel),
            [
                {"content_block_id": identifier, "locale": locale, "label": label}
                for locale, label in translations.items()
            ],
        )
