from sqlalchemy import insert, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.catalog.domain.product.aggregate import (
    Product,
    ProductVariant,
    VariantSelection,
)
from src.modules.catalog.domain.product.error import ProductIdentifierAlreadyExistsError
from src.modules.catalog.domain.product.value_object.content import ProductContentVO
from src.modules.catalog.domain.product.value_object.identifier import (
    ProductIdVO,
    VariantIdVO,
)
from src.modules.catalog.domain.product.value_object.locale import ProductLocaleVO
from src.modules.catalog.infrastructure.persistence.models.content import (
    ProductContentModel,
)
from src.modules.catalog.infrastructure.persistence.models.product import ProductModel
from src.modules.catalog.infrastructure.persistence.models.variant import VariantModel
from src.modules.catalog.infrastructure.persistence.models.variant_selection import (
    VariantSelectionModel,
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
            selections = [
                dict(
                    variant_id=variant.id.uuid,
                    attribute_id=item.attribute_id.uuid,
                    option_id=item.option_id.uuid,
                )
                for variant in product.variants
                for item in variant.selections
            ]
            if selections:
                await self._session.execute(insert(VariantSelectionModel), selections)
            if product.contents:
                await self._session.execute(
                    insert(ProductContentModel),
                    [
                        ProductMapper.content_values(product.id.uuid, content)
                        for content in product.contents.values()
                    ],
                )
        except IntegrityError as exc:
            original = exc.orig
            constraint = getattr(original, "constraint_name", None) or getattr(
                original.__cause__, "constraint_name", None
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
        selections = (
            (
                await self._session.execute(
                    select(VariantSelectionModel)
                    .join(
                        VariantModel,
                        VariantModel.id == VariantSelectionModel.variant_id,
                    )
                    .where(VariantModel.product_id == product_id.uuid)
                )
            )
            .scalars()
            .all()
        )
        by_variant = {}
        for item in selections:
            by_variant.setdefault(item.variant_id, []).append(
                VariantSelection(
                    EntityIdVO.from_value(item.attribute_id),
                    EntityIdVO.from_value(item.option_id),
                )
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
        return Product(
            id=ProductIdVO.from_value(row.id),
            product_type=row.type,
            variants=tuple(
                ProductVariant(
                    VariantIdVO.from_value(variant.id),
                    EntityIdVO.from_value(variant.sku_id),
                    tuple(by_variant.get(variant.id, ())),
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
                    name=item.name,
                    description=item.description,
                )
                for item in content_rows
            },
        )

    async def save_content(self, product: Product, locale: ProductLocaleVO) -> None:
        content = product.contents[locale.value]
        values = ProductMapper.content_values(product.id.uuid, content)
        statement = pg_insert(ProductContentModel).values(values)
        await self._session.execute(
            statement.on_conflict_do_update(
                constraint="pk_catalog_product_contents",
                set_={field: values[field] for field in ("name", "description")},
            )
        )
        await self._session.execute(
            update(ProductModel)
            .where(ProductModel.id == product.id.uuid)
            .values(updated_at=product.updated_at, updated_by=product.updated_by.uuid)
        )
