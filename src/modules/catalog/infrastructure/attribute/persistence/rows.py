from src.modules.catalog.infrastructure.persistence.models.attribute_translation import (
    AttributeTranslationModel,
)
from src.modules.catalog.infrastructure.persistence.models.attribute_option import (
    AttributeOptionModel,
)
from src.modules.catalog.infrastructure.persistence.models.attribute_option_translation import (
    AttributeOptionTranslationModel,
)

from uuid import UUID
from typing import Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


async def read_attribute_parts(
    session: AsyncSession, identifier: UUID
) -> tuple[dict[str, str], tuple[dict[str, Any], ...]]:
    """Читает технические части хранения; не создаёт Domain или DTO."""
    translations = dict(
        (
            await session.execute(
                select(
                    AttributeTranslationModel.locale, AttributeTranslationModel.label
                ).where(AttributeTranslationModel.attribute_id == identifier)
            )
        ).all()
    )
    rows = (
        (
            await session.execute(
                select(AttributeOptionModel.__table__)
                .where(AttributeOptionModel.attribute_id == identifier)
                .order_by(AttributeOptionModel.position, AttributeOptionModel.id)
            )
        )
        .mappings()
        .all()
    )
    labels = (
        (
            await session.execute(
                select(AttributeOptionTranslationModel.__table__)
                .join(
                    AttributeOptionModel,
                    AttributeOptionModel.id
                    == AttributeOptionTranslationModel.option_id,
                )
                .where(AttributeOptionModel.attribute_id == identifier)
            )
        )
        .mappings()
        .all()
    )
    by_id: dict[UUID, dict[str, str]] = {}
    for label in labels:
        by_id.setdefault(label["option_id"], {})[label["locale"]] = label["label"]
    return translations, tuple(
        {**row, "translations": by_id.get(row["id"], {})} for row in rows
    )
