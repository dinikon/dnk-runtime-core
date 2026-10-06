from sqlalchemy import delete, insert, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.catalog.domain.product.aggregate import (
    Product,
    ProductVariant,
)
from src.modules.catalog.domain.product.error import ProductIdentifierAlreadyExistsError
from src.modules.catalog.domain.product.value_object.content import ProductContentVO
from src.modules.catalog.domain.product.value_object.identifier import (
    ProductIdVO,
    VariantIdVO,
)
from src.modules.catalog.domain.product.value_object.kind import ProductKind
from src.modules.catalog.domain.product.value_object.locale import ProductLocaleVO
from src.modules.catalog.infrastructure.persistence.models.content import (
    ProductContentModel,
)
from src.modules.catalog.infrastructure.persistence.models.product_content_value import (
    ProductContentValueModel,
)
from src.modules.catalog.infrastructure.persistence.models.variant_content_value import (
    VariantContentValueModel,
)
from src.modules.catalog.infrastructure.persistence.models.product import ProductModel
from src.modules.catalog.infrastructure.persistence.models.variant import VariantModel
from src.modules.catalog.infrastructure.persistence.models.variant_content import (
    VariantContentModel,
)
from src.modules.catalog.infrastructure.persistence.models.product_category import (
    ProductCategoryModel,
)
from src.modules.catalog.domain.category.value_object.identifier import CategoryIdVO
from src.modules.catalog.domain.product_type.value_object.product_type_id import (
    ProductTypeIdVO,
)
from src.modules.catalog.infrastructure.product.persistence.mapper import ProductMapper
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


class SqlAlchemyProductRepository:
    """Пишет Product через общую tenant-сессию без собственного commit."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, product: Product) -> None:
        try:
            await self._session.execute(
                insert(ProductModel).values(ProductMapper.product_values(product))
            )
            await self._session.execute(
                insert(VariantModel),
                [
                    ProductMapper.variant_values(product, variant)
                    for variant in product.variants
                ],
            )
            if product.contents:
                await self._session.execute(
                    insert(ProductContentModel),
                    [
                        ProductMapper.content_values(product.id.uuid, content)
                        for content in product.contents.values()
                    ],
                )
                values = [
                    {
                        "product_id": product.id.uuid,
                        "locale_code": content.locale.value,
                        "block_id": block_id,
                        "value": value,
                    }
                    for content in product.contents.values()
                    for block_id, value in content.values.items()
                ]
                if values:
                    await self._session.execute(
                        insert(ProductContentValueModel), values
                    )
        except IntegrityError as exc:
            original = exc.orig
            constraint = getattr(original, "constraint_name", None) or getattr(
                getattr(original, "__cause__", None), "constraint_name", None
            )
            if getattr(original, "sqlstate", None) == "23505" and constraint in {
                "pk_catalog_products",
                "pk_catalog_variants",
            }:
                raise ProductIdentifierAlreadyExistsError(
                    "Product identifier already exists."
                ) from exc
            raise

    async def get_for_update(self, product_id: ProductIdVO) -> Product | None:
        row = (
            await self._session.execute(
                select(ProductModel)
                .where(ProductModel.id == product_id.uuid)
                .with_for_update()
            )
        ).scalar_one_or_none()
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
        variant_content_rows = (
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
        variant_value_rows = (
            (
                await self._session.execute(
                    select(VariantContentValueModel)
                    .join(
                        VariantModel,
                        VariantContentValueModel.variant_id == VariantModel.id,
                    )
                    .where(VariantModel.product_id == product_id.uuid)
                )
            )
            .scalars()
            .all()
        )
        content_rows = (
            (
                await self._session.execute(
                    select(ProductContentModel).where(
                        ProductContentModel.product_id == product_id.uuid
                    )
                )
            )
            .scalars()
            .all()
        )
        product_value_rows = (
            (
                await self._session.execute(
                    select(ProductContentValueModel).where(
                        ProductContentValueModel.product_id == product_id.uuid
                    )
                )
            )
            .scalars()
            .all()
        )
        category_rows = (
            (
                await self._session.execute(
                    select(ProductCategoryModel)
                    .where(ProductCategoryModel.product_id == product_id.uuid)
                    .order_by(ProductCategoryModel.category_id)
                )
            )
            .scalars()
            .all()
        )
        return Product.restore(
            product_id=ProductIdVO.from_value(row.id),
            product_type_id=ProductTypeIdVO.from_value(row.product_type_id),
            kind=ProductKind(row.kind),
            variants=tuple(
                ProductVariant(
                    VariantIdVO.from_value(variant.id),
                    EntityIdVO.from_value(variant.sku_id),
                    {
                        item.locale_code: ProductContentVO(
                            ProductLocaleVO(item.locale_code),
                            {
                                value.block_id: value.value
                                for value in variant_value_rows
                                if value.variant_id == variant.id
                                and value.locale_code == item.locale_code
                            },
                        )
                        for item in variant_content_rows
                        if item.variant_id == variant.id
                    },
                )
                for variant in variants
            ),
            created_at=row.created_at,
            updated_at=row.updated_at,
            created_by=EntityIdVO.from_value(row.created_by),
            updated_by=EntityIdVO.from_value(row.updated_by),
            contents={
                item.locale_code: ProductContentVO(
                    locale=ProductLocaleVO(item.locale_code),
                    values={
                        value.block_id: value.value
                        for value in product_value_rows
                        if value.locale_code == item.locale_code
                    },
                )
                for item in content_rows
            },
            category_ids=tuple(
                CategoryIdVO.from_value(item.category_id) for item in category_rows
            ),
            primary_category_id=next(
                (
                    CategoryIdVO.from_value(item.category_id)
                    for item in category_rows
                    if item.is_primary
                ),
                None,
            ),
        )

    async def save_content(self, product: Product, locale: ProductLocaleVO) -> None:
        await self._session.execute(
            delete(ProductContentModel).where(
                ProductContentModel.product_id == product.id.uuid,
                ProductContentModel.locale_code == locale.value,
            )
        )
        content = product.contents.get(locale.value)
        if content is not None:
            await self._session.execute(
                insert(ProductContentModel).values(
                    ProductMapper.content_values(product.id.uuid, content)
                )
            )
            if content.values:
                await self._session.execute(
                    insert(ProductContentValueModel),
                    [
                        {
                            "product_id": product.id.uuid,
                            "locale_code": locale.value,
                            "block_id": block_id,
                            "value": value,
                        }
                        for block_id, value in content.values.items()
                    ],
                )
        await self._session.execute(
            update(ProductModel)
            .where(ProductModel.id == product.id.uuid)
            .values(updated_at=product.updated_at, updated_by=product.updated_by.uuid)
        )

    async def save_categories(self, product: Product) -> None:
        await self._session.execute(
            delete(ProductCategoryModel).where(
                ProductCategoryModel.product_id == product.id.uuid
            )
        )
        if product.category_ids:
            await self._session.execute(
                insert(ProductCategoryModel),
                [
                    {
                        "product_id": product.id.uuid,
                        "category_id": category_id.uuid,
                        "is_primary": category_id == product.primary_category_id,
                    }
                    for category_id in product.category_ids
                ],
            )
        await self._session.execute(
            update(ProductModel)
            .where(ProductModel.id == product.id.uuid)
            .values(updated_at=product.updated_at, updated_by=product.updated_by.uuid)
        )

    async def save_variants(self, product: Product) -> None:
        desired = {item.id.uuid: item for item in product.variants}
        existing = set(
            (
                await self._session.execute(
                    select(VariantModel.id).where(
                        VariantModel.product_id == product.id.uuid
                    )
                )
            ).scalars()
        )
        removed = existing - desired.keys()
        if removed:
            await self._session.execute(
                delete(VariantModel).where(
                    VariantModel.product_id == product.id.uuid,
                    VariantModel.id.in_(removed),
                )
            )
        for variant_id, variant in desired.items():
            if variant_id in existing:
                await self._session.execute(
                    update(VariantModel)
                    .where(
                        VariantModel.id == variant_id,
                        VariantModel.product_id == product.id.uuid,
                    )
                    .values(sku_id=variant.sku_id.uuid)
                )
            else:
                await self._session.execute(
                    insert(VariantModel).values(
                        ProductMapper.variant_values(product, variant)
                    )
                )
            for locale in variant.contents:
                await self.save_variant_content(
                    product, variant.id, ProductLocaleVO(locale)
                )
        await self._session.execute(
            update(ProductModel)
            .where(ProductModel.id == product.id.uuid)
            .values(
                kind=product.kind.value,
                updated_at=product.updated_at,
                updated_by=product.updated_by.uuid,
            )
        )

    async def save_variant_content(
        self, product: Product, variant_id: VariantIdVO, locale: ProductLocaleVO
    ) -> None:
        await self._session.execute(
            delete(VariantContentModel).where(
                VariantContentModel.variant_id == variant_id.uuid,
                VariantContentModel.locale_code == locale.value,
            )
        )
        content = product.get_variant(variant_id).contents.get(locale.value)
        if content is not None:
            await self._session.execute(
                insert(VariantContentModel).values(
                    variant_id=variant_id.uuid, locale_code=locale.value
                )
            )
            if content.values:
                await self._session.execute(
                    insert(VariantContentValueModel),
                    [
                        {
                            "variant_id": variant_id.uuid,
                            "locale_code": locale.value,
                            "block_id": block_id,
                            "value": value,
                        }
                        for block_id, value in content.values.items()
                    ],
                )
        await self._session.execute(
            update(ProductModel)
            .where(ProductModel.id == product.id.uuid)
            .values(updated_at=product.updated_at, updated_by=product.updated_by.uuid)
        )

    async def delete(self, product: Product) -> None:
        await self._session.execute(
            delete(ProductModel).where(ProductModel.id == product.id.uuid)
        )

    async def save_type(self, product: Product) -> None:
        await self._session.execute(
            update(ProductModel)
            .where(ProductModel.id == product.id.uuid)
            .values(
                product_type_id=product.product_type_id.uuid,
                updated_at=product.updated_at,
                updated_by=product.updated_by.uuid,
            )
        )
