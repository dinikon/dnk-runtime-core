from typing import Any
from collections.abc import Mapping
from sqlalchemy import select, func, or_, cast, String
from sqlalchemy.ext.asyncio import AsyncSession
from src.modules.catalog.domain.product.value_object.identifier import ProductIdVO
from src.modules.catalog.domain.product_type.value_object.identifier import (
    ProductTypeIdVO,
)
from src.modules.catalog.domain.product.value_object.variant_id import VariantIdVO
from src.modules.catalog.infrastructure.product.persistence.query_mapper import (
    ProductQueryMapper,
)
from src.modules.catalog.infrastructure.product.persistence.structure_rows import (
    read_product_structure,
)
from src.modules.catalog.infrastructure.product.persistence.product_translations import (
    read_product_translations,
)
from src.modules.catalog.infrastructure.persistence.models.product import ProductModel
from src.modules.catalog.infrastructure.persistence.models.product_type import (
    ProductTypeModel,
)
from src.modules.catalog.infrastructure.persistence.models.variant import VariantModel
from src.modules.catalog.infrastructure.persistence.models.product_content_value import (
    ProductContentValueModel,
)
from src.modules.catalog.infrastructure.persistence.models.content_block import (
    ContentBlockModel,
)
from src.modules.catalog.infrastructure.persistence.models.product_type_block import (
    ProductTypeBlockModel,
)
from src.modules.catalog.application.product.query.get_product.dto import (
    GetProductDetailsDTO,
)
from src.modules.catalog.application.product.query.list_products.dto import (
    ListProductsPageDTO,
)
from src.modules.catalog.application.product.query.get_variant.dto import (
    GetVariantDetailsDTO,
)


class SqlAlchemyProductQueryRepository:
    """Читает согласованные SQL-проекции Product без восстановления агрегатов."""

    def __init__(self, session: AsyncSession) -> None:
        """Получает общую tenant-сессию внешнего UoW."""
        self._session = session

    async def _row(self, identifier: ProductIdVO) -> Mapping[str, Any] | None:
        """Читает корень и версию схемы без JOIN, размножающего позиции."""
        return (
            (
                await self._session.execute(
                    select(ProductModel.__table__, ProductTypeModel.schema_version)
                    .join(
                        ProductTypeModel,
                        ProductTypeModel.id == ProductModel.product_type_id,
                    )
                    .where(ProductModel.id == identifier.uuid)
                )
            )
            .mappings()
            .one_or_none()
        )

    async def _projection(self, row: Mapping[str, Any]) -> dict[str, Any]:
        """Собирает техническую проекцию контента и системной роли Title."""
        links = (
            await self._session.execute(
                select(ContentBlockModel.id, ProductTypeBlockModel.scope)
                .join(
                    ProductTypeBlockModel,
                    ProductTypeBlockModel.block_id == ContentBlockModel.id,
                )
                .where(
                    ProductTypeBlockModel.product_type_id == row["product_type_id"],
                    ContentBlockModel.code == "title",
                    ContentBlockModel.is_system.is_(True),
                )
            )
        ).all()
        titles = {scope: identifier for identifier, scope in links}
        return {
            **row,
            "translations": await read_product_translations(self._session, row["id"]),
            "title_id": titles.get("PRODUCT"),
            "variant_title_id": titles.get("VARIANT"),
        }

    async def get_details(
        self, identifier: ProductIdVO, locale: str
    ) -> GetProductDetailsDTO | None:
        """Читает карточку с позициями и null для отсутствующих переводов."""
        row = await self._row(identifier)
        if row is None:
            return None
        return ProductQueryMapper.to_details(
            {
                **await self._projection(row),
                **await read_product_structure(self._session, identifier.uuid),
            },
            locale,
        )

    async def list_page(
        self,
        locale: str,
        search: str,
        page: int,
        page_size: int,
        product_type_id: ProductTypeIdVO | None = None,
        kind: str | None = None,
    ) -> ListProductsPageDTO:
        """Считает товары, а количество позиций получает коррелированным подзапросом."""
        statement = select(
            ProductModel.__table__,
            ProductTypeModel.schema_version,
            select(func.count())
            .select_from(VariantModel)
            .where(VariantModel.product_id == ProductModel.id)
            .correlate(ProductModel)
            .scalar_subquery()
            .label("variant_count"),
        ).join(ProductTypeModel, ProductTypeModel.id == ProductModel.product_type_id)
        if search:
            escaped = (
                search.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            )
            statement = statement.where(
                or_(
                    select(ProductContentValueModel.product_id)
                    .where(
                        ProductContentValueModel.product_id == ProductModel.id,
                        ProductContentValueModel.locale == locale,
                        ProductContentValueModel.value.ilike(
                            "%" + escaped + "%", escape="\\"
                        ),
                    )
                    .exists(),
                    cast(ProductModel.id, String).ilike(
                        "%" + escaped + "%", escape="\\"
                    ),
                )
            )
        if product_type_id is not None:
            statement = statement.where(
                ProductModel.product_type_id == product_type_id.uuid
            )
        if kind is not None:
            statement = statement.where(ProductModel.kind == kind)
        total = await self._session.scalar(
            select(func.count()).select_from(statement.subquery())
        )
        rows = (
            (
                await self._session.execute(
                    statement.order_by(ProductModel.created_at.desc(), ProductModel.id)
                    .offset((page - 1) * page_size)
                    .limit(page_size)
                )
            )
            .mappings()
            .all()
        )
        items = tuple(
            [
                ProductQueryMapper.to_list_item(await self._projection(row), locale)
                for row in rows
            ]
        )
        return ListProductsPageDTO(items, total or 0, page, page_size)

    async def get_variant(
        self, product_id: ProductIdVO, variant_id: VariantIdVO, locale: str
    ) -> GetVariantDetailsDTO | None:
        """Проверяет обе идентичности перед созданием проекции позиции."""
        row = await self._row(product_id)
        if row is None:
            return None
        parts = await read_product_structure(self._session, product_id.uuid)
        variant = next(
            (v for v in parts["variants"] if v["id"] == variant_id.uuid), None
        )
        return (
            None
            if variant is None
            else ProductQueryMapper.to_variant(
                await self._projection(row), variant, locale
            )
        )
