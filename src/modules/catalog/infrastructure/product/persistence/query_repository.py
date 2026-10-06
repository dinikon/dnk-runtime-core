from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.catalog.application.product.query.get_product.dto import (
    ProductContentDTO,
    ProductDetailsDTO,
    ProductCategoryDTO,
    ProductVariantDTO,
)
from src.modules.catalog.application.product.query.list_products.dto import (
    ProductListItemDTO,
)
from src.modules.catalog.domain.product.value_object.identifier import ProductIdVO
from src.modules.catalog.domain.product.value_object.kind import ProductKind
from src.modules.catalog.domain.product.value_object.locale import ProductLocaleVO
from src.modules.catalog.infrastructure.persistence.models.content import (
    ProductContentModel,
)
from src.modules.catalog.infrastructure.persistence.models.content_value import (
    ProductContentValueModel,
    VariantContentValueModel,
)
from src.modules.catalog.infrastructure.persistence.models.content_block import (
    ContentBlockDefinitionModel,
)
from src.modules.catalog.infrastructure.persistence.models.product_type import (
    ProductTypeModel,
)
from src.modules.catalog.infrastructure.persistence.models.product import ProductModel
from src.modules.catalog.infrastructure.persistence.models.variant import VariantModel
from src.modules.catalog.infrastructure.persistence.models.variant_content import (
    VariantContentModel,
)
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
        variant_contents = (
            (
                await self._session.execute(
                    select(VariantContentModel)
                    .join(
                        VariantModel, VariantContentModel.variant_id == VariantModel.id
                    )
                    .where(VariantModel.product_id == product_id.uuid)
                )
            )
            .scalars()
            .all()
        )
        variant_values = (
            await self._session.execute(
                select(
                    VariantContentValueModel.variant_id,
                    VariantContentValueModel.locale_code,
                    ContentBlockDefinitionModel.code,
                    VariantContentValueModel.value,
                )
                .join(
                    VariantModel, VariantContentValueModel.variant_id == VariantModel.id
                )
                .join(
                    ContentBlockDefinitionModel,
                    ContentBlockDefinitionModel.id == VariantContentValueModel.block_id,
                )
                .where(VariantModel.product_id == product_id.uuid)
            )
        ).all()
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
        values = (
            await self._session.execute(
                select(
                    ProductContentValueModel.locale_code,
                    ContentBlockDefinitionModel.code,
                    ProductContentValueModel.value,
                )
                .join(
                    ContentBlockDefinitionModel,
                    ContentBlockDefinitionModel.id == ProductContentValueModel.block_id,
                )
                .where(ProductContentValueModel.product_id == product_id.uuid)
            )
        ).all()
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
            kind=ProductKind(row.kind),
            product_type_id=row.product_type_id,
            schema_version=(
                await self._session.scalar(
                    select(ProductTypeModel.schema_version).where(
                        ProductTypeModel.id == row.product_type_id
                    )
                )
            )
            or 1,
            variant_id=variant[0].id,
            sku_id=variant[0].sku_id,
            sku_code=None,
            requested_locale=locale.value,
            content_locales=tuple(item.locale_code for item in contents),
            content=(
                ProductContentDTO(
                    locale=matching.locale_code,
                    blocks={
                        value.code: value.value
                        for value in values
                        if value.locale_code == matching.locale_code
                    },
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
            variants=tuple(
                ProductVariantDTO(
                    id=item.id,
                    sku_id=item.sku_id,
                    sku_code=None,
                    content_locales=tuple(
                        sorted(
                            content.locale_code
                            for content in variant_contents
                            if content.variant_id == item.id
                        )
                    ),
                    content=(
                        ProductContentDTO(
                            locale.value,
                            {
                                value.code: value.value
                                for value in variant_values
                                if value.variant_id == item.id
                                and value.locale_code == locale.value
                            },
                        )
                        if any(
                            content.variant_id == item.id
                            and content.locale_code == locale.value
                            for content in variant_contents
                        )
                        else None
                    ),
                )
                for item in variant
            ),
        )

    async def list_products(
        self, locale: ProductLocaleVO
    ) -> tuple[ProductListItemDTO, ...]:
        counts = (
            select(
                VariantModel.product_id,
                func.count(VariantModel.id).label("variant_count"),
            )
            .group_by(VariantModel.product_id)
            .subquery()
        )
        title = (
            select(ProductContentValueModel.value)
            .join(
                ContentBlockDefinitionModel,
                ContentBlockDefinitionModel.id == ProductContentValueModel.block_id,
            )
            .where(
                ProductContentValueModel.product_id == ProductModel.id,
                ProductContentValueModel.locale_code == locale.value,
                ContentBlockDefinitionModel.code == "title",
            )
            .correlate(ProductModel)
            .scalar_subquery()
        )
        rows = (
            await self._session.execute(
                select(
                    ProductModel.id,
                    ProductModel.kind,
                    title.label("name"),
                    counts.c.variant_count,
                    ProductCategoryModel.category_id,
                    CategoryContentModel.name.label("category_name"),
                    ProductModel.updated_at,
                )
                .outerjoin(counts, counts.c.product_id == ProductModel.id)
                .outerjoin(
                    ProductCategoryModel,
                    (ProductCategoryModel.product_id == ProductModel.id)
                    & ProductCategoryModel.is_primary,
                )
                .outerjoin(
                    CategoryContentModel,
                    (
                        CategoryContentModel.category_id
                        == ProductCategoryModel.category_id
                    )
                    & (CategoryContentModel.locale_code == locale.value),
                )
                .order_by(ProductModel.updated_at.desc(), ProductModel.id)
            )
        ).all()
        return tuple(
            ProductListItemDTO(
                row.id,
                ProductKind(row.kind),
                row.name,
                row.variant_count or 0,
                row.category_id,
                row.category_name,
                row.updated_at,
            )
            for row in rows
        )
