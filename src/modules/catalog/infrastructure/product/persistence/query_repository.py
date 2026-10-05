from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.catalog.application.product.query.get_product.dto import (
    ProductContentDTO,
    ProductDetailsDTO,
    ProductSelectionDTO,
    ProductVariantDTO,
    VariableProductDetailsDTO,
)
from src.modules.catalog.domain.product.value_object.identifier import ProductIdVO
from src.modules.catalog.domain.product.value_object.locale import ProductLocaleVO
from src.modules.catalog.infrastructure.persistence.models.attribute import (
    AttributeModel,
)
from src.modules.catalog.infrastructure.persistence.models.attribute_content import (
    AttributeContentModel,
)
from src.modules.catalog.infrastructure.persistence.models.attribute_option import (
    AttributeOptionModel,
)
from src.modules.catalog.infrastructure.persistence.models.content import (
    ProductContentModel,
)
from src.modules.catalog.infrastructure.persistence.models.option_content import (
    OptionContentModel,
)
from src.modules.catalog.infrastructure.persistence.models.product import ProductModel
from src.modules.catalog.infrastructure.persistence.models.variant import VariantModel
from src.modules.catalog.infrastructure.persistence.models.variant_selection import (
    VariantSelectionModel,
)


class SqlAlchemyProductQueryRepository:
    """Читает SIMPLE или VARIABLE без восстановления доменного агрегата."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_details(
        self, product_id: ProductIdVO, locale: ProductLocaleVO
    ) -> ProductDetailsDTO | VariableProductDetailsDTO | None:
        row = await self._session.get(ProductModel, product_id.uuid)
        if row is None:
            return None
        variants = (
            (
                await self._session.execute(
                    select(VariantModel)
                    .where(VariantModel.product_id == product_id.uuid)
                    .order_by(VariantModel.id)
                )
            )
            .scalars()
            .all()
        )
        contents = (
            (
                await self._session.execute(
                    select(ProductContentModel)
                    .where(ProductContentModel.product_id == product_id.uuid)
                    .order_by(ProductContentModel.locale_code)
                )
            )
            .scalars()
            .all()
        )
        matching = next(
            (item for item in contents if item.locale_code == locale.value), None
        )
        common = dict(
            id=row.id,
            type=row.type,
            requested_locale=locale.value,
            content_locales=tuple(item.locale_code for item in contents),
            content=(
                ProductContentDTO(
                    locale=matching.locale_code,
                    name=matching.name,
                    description=matching.description,
                )
                if matching is not None
                else None
            ),
            created_at=row.created_at,
            updated_at=row.updated_at,
            created_by=row.created_by,
            updated_by=row.updated_by,
        )
        if row.type == "SIMPLE":
            variant = variants[0]
            return ProductDetailsDTO(
                variant_id=variant.id,
                sku_id=variant.sku_id,
                sku_code=None,
                **common,
            )
        selections = (
            await self._session.execute(
                select(
                    VariantSelectionModel.variant_id,
                    VariantSelectionModel.attribute_id,
                    AttributeModel.code,
                    AttributeContentModel.name,
                    VariantSelectionModel.option_id,
                    AttributeOptionModel.code,
                    OptionContentModel.name,
                )
                .join(
                    AttributeModel,
                    AttributeModel.id == VariantSelectionModel.attribute_id,
                )
                .join(
                    AttributeOptionModel,
                    AttributeOptionModel.id == VariantSelectionModel.option_id,
                )
                .outerjoin(
                    AttributeContentModel,
                    (AttributeContentModel.attribute_id == AttributeModel.id)
                    & (AttributeContentModel.locale_code == locale.value),
                )
                .outerjoin(
                    OptionContentModel,
                    (OptionContentModel.option_id == AttributeOptionModel.id)
                    & (OptionContentModel.locale_code == locale.value),
                )
                .join(VariantModel, VariantModel.id == VariantSelectionModel.variant_id)
                .where(VariantModel.product_id == product_id.uuid)
                .order_by(VariantSelectionModel.attribute_id)
            )
        ).all()
        by_variant: dict = {}
        for (
            variant_id,
            attribute_id,
            attribute_code,
            attribute_name,
            option_id,
            option_code,
            option_name,
        ) in selections:
            by_variant.setdefault(variant_id, []).append(
                ProductSelectionDTO(
                    attribute_id=attribute_id,
                    attribute_code=attribute_code,
                    attribute_name=attribute_name,
                    option_id=option_id,
                    option_code=option_code,
                    option_name=option_name,
                )
            )
        return VariableProductDetailsDTO(
            variants=tuple(
                ProductVariantDTO(
                    id=variant.id,
                    sku_id=variant.sku_id,
                    sku_code=None,
                    selections=tuple(by_variant.get(variant.id, ())),
                )
                for variant in variants
            ),
            **common,
        )
