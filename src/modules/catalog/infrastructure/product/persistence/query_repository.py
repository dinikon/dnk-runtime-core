from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.catalog.application.product.query.get_product.dto import (
    ProductContentDTO,
    ProductDetailsDTO,
    ProductCategoryDTO,
)
from src.modules.catalog.domain.product.value_object.identifier import ProductIdVO
from src.modules.catalog.domain.product.value_object.locale import ProductLocaleVO
from src.modules.catalog.infrastructure.persistence.models.content import (
    ProductContentModel,
)
from src.modules.catalog.infrastructure.persistence.models.product import ProductModel
from src.modules.catalog.infrastructure.persistence.models.variant import VariantModel
from src.modules.catalog.infrastructure.persistence.models.category_content import (
    CategoryContentModel,
)
from src.modules.catalog.infrastructure.persistence.models.product_category import (
    ProductCategoryModel,
)


class SqlAlchemyProductQueryRepository:
    """Читает SIMPLE-карточку без восстановления доменного агрегата."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_details(
        self, product_id: ProductIdVO, locale: ProductLocaleVO
    ) -> ProductDetailsDTO | None:
        row = await self._session.get(ProductModel, product_id.uuid)
        if row is None:
            return None
        variant = (
            await self._session.execute(
                select(VariantModel).where(VariantModel.product_id == product_id.uuid)
            )
        ).scalar_one()
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
        category_rows = (
            await self._session.execute(
                select(
                    ProductCategoryModel.category_id,
                    ProductCategoryModel.is_primary,
                    CategoryContentModel.name,
                )
                .outerjoin(
                    CategoryContentModel,
                    (
                        CategoryContentModel.category_id
                        == ProductCategoryModel.category_id
                    )
                    & (CategoryContentModel.locale_code == locale.value),
                )
                .where(ProductCategoryModel.product_id == product_id.uuid)
                .order_by(ProductCategoryModel.category_id)
            )
        ).all()
        return ProductDetailsDTO(
            id=row.id,
            type=row.type,
            variant_id=variant.id,
            sku_id=variant.sku_id,
            sku_code=None,
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
            categories=tuple(
                ProductCategoryDTO(item.category_id, item.name)
                for item in category_rows
            ),
            primary_category_id=next(
                (item.category_id for item in category_rows if item.is_primary), None
            ),
            created_at=row.created_at,
            updated_at=row.updated_at,
            created_by=row.created_by,
            updated_by=row.updated_by,
        )
