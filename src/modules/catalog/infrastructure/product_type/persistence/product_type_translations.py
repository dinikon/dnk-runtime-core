from uuid import UUID
from sqlalchemy import select, insert, delete
from sqlalchemy.ext.asyncio import AsyncSession
from src.modules.catalog.infrastructure.persistence.models.product_type_translation import (
    ProductTypeTranslationModel,
)


async def read_product_type_translations(
    session: AsyncSession, identifier: UUID
) -> dict[str, str]:
    """Читает табличные части product_type для write restoration либо read projection."""
    rows = (
        (
            await session.execute(
                select(ProductTypeTranslationModel.__table__).where(
                    ProductTypeTranslationModel.product_type_id == identifier
                )
            )
        )
        .mappings()
        .all()
    )
    return {r["locale"]: r["label"] for r in rows}


async def save_product_type_translations(
    session: AsyncSession, identifier: UUID, translations: dict[str, str]
) -> None:
    """Заменяет принадлежащие агрегату переводы без commit и бизнес-валидации."""
    await session.execute(
        delete(ProductTypeTranslationModel).where(
            ProductTypeTranslationModel.product_type_id == identifier
        )
    )
    if translations:
        await session.execute(
            insert(ProductTypeTranslationModel),
            [
                {"product_type_id": identifier, "locale": locale, "label": label}
                for locale, label in translations.items()
            ],
        )
