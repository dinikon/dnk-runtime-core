from src.modules.catalog.infrastructure.persistence.models.product_attribute_value import (
    ProductAttributeValueModel,
)
from src.modules.catalog.infrastructure.persistence.models.product_category import (
    ProductCategoryModel,
)
from src.modules.catalog.infrastructure.persistence.models.product_tag import (
    ProductTagModel,
)
from uuid import UUID
from typing import Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
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
from src.modules.catalog.infrastructure.product.persistence.variant_translations import (
    read_variant_translations,
)


async def read_product_structure(
    session: AsyncSession, identifier: UUID
) -> dict[str, Any]:
    """Читает технические строки структуры, не проверяя инварианты или создавая Domain."""
    axes = (
        (
            await session.execute(
                select(ProductAxisModel.__table__)
                .where(ProductAxisModel.product_id == identifier)
                .order_by(ProductAxisModel.position)
            )
        )
        .mappings()
        .all()
    )
    options = (
        (
            await session.execute(
                select(ProductAxisOptionModel.__table__)
                .where(ProductAxisOptionModel.product_id == identifier)
                .order_by(ProductAxisOptionModel.option_id)
            )
        )
        .mappings()
        .all()
    )
    selections = (
        (
            await session.execute(
                select(VariantSelectionModel.__table__).where(
                    VariantSelectionModel.product_id == identifier
                )
            )
        )
        .mappings()
        .all()
    )
    defaults = (
        await session.execute(
            select(
                ProductDefaultSelectionModel.attribute_id,
                ProductDefaultSelectionModel.option_id,
            ).where(ProductDefaultSelectionModel.product_id == identifier)
        )
    ).all()
    rows = (
        (
            await session.execute(
                select(VariantModel.__table__)
                .where(VariantModel.product_id == identifier)
                .order_by(VariantModel.id)
            )
        )
        .mappings()
        .all()
    )
    variants = []
    for row in rows:
        variants.append(
            {
                **row,
                "translations": await read_variant_translations(session, row["id"]),
                "selection": {
                    str(s["attribute_id"]): str(s["option_id"])
                    for s in selections
                    if s["variant_id"] == row["id"]
                },
            }
        )
    attributes = (
        (
            await session.execute(
                select(ProductAttributeValueModel.__table__)
                .where(ProductAttributeValueModel.product_id == identifier)
                .order_by(ProductAttributeValueModel.position)
            )
        )
        .mappings()
        .all()
    )
    categories = (
        (
            await session.execute(
                select(ProductCategoryModel.__table__)
                .where(ProductCategoryModel.product_id == identifier)
                .order_by(ProductCategoryModel.category_id)
            )
        )
        .mappings()
        .all()
    )
    tags = (
        await session.scalars(
            select(ProductTagModel.tag_id)
            .where(ProductTagModel.product_id == identifier)
            .order_by(ProductTagModel.tag_id)
        )
    ).all()
    return {
        "attribute_values": tuple(attributes),
        "categories": tuple(categories),
        "tag_ids": tuple(tags),
        "axes": tuple(
            {
                **a,
                "option_ids": tuple(
                    o["option_id"]
                    for o in options
                    if o["attribute_id"] == a["attribute_id"]
                ),
            }
            for a in axes
        ),
        "variants": tuple(variants),
        "default_selection": (
            None if not defaults else {str(a): str(o) for a, o in defaults}
        ),
    }
