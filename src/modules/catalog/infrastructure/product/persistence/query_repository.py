from typing import Any
from collections.abc import Mapping
from src.modules.catalog.infrastructure.product.persistence.variant_translations import (
    read_variant_translations,
)
from src.modules.catalog.infrastructure.persistence.models.product_content_value import (
    ProductContentValueModel,
)
from src.modules.catalog.infrastructure.product.persistence.product_translations import (
    read_product_translations,
)
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
from src.modules.catalog.infrastructure.persistence.models.product import ProductModel
from src.modules.catalog.infrastructure.persistence.models.product_type import (
    ProductTypeModel,
)
from src.modules.catalog.infrastructure.persistence.models.variant import VariantModel
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
    """Читает SQL-проекции в уже выбранной tenant-схеме."""

    def __init__(self, session: AsyncSession) -> None:
        """Получает сессию внешнего UoW."""
        self._session = session

    async def get_details(
        self, identifier: ProductIdVO, locale: str
    ) -> GetProductDetailsDTO | None:
        """Возвращает карточку и null при отсутствии перевода выбранной locale."""
        row = (
            (
                await self._session.execute(
                    select(
                        ProductModel.__table__,
                        ProductTypeModel.schema_version,
                        VariantModel.id.label("variant_id"),
                        VariantModel.virtual,
                        VariantModel.downloadable,
                    )
                    .join(
                        ProductTypeModel,
                        ProductTypeModel.id == ProductModel.product_type_id,
                    )
                    .join(VariantModel, VariantModel.product_id == ProductModel.id)
                    .where(ProductModel.id == identifier.uuid)
                )
            )
            .mappings()
            .one_or_none()
        )
        if row is None:
            return None
        return ProductQueryMapper.to_details(await self._projection(row), locale)

    async def list_page(
        self,
        locale: str,
        search: str,
        page: int,
        page_size: int,
        product_type_id: ProductTypeIdVO | None = None,
    ) -> ListProductsPageDTO:
        """Читает страницу и total с одинаковыми серверными фильтрами."""
        statement = (
            select(
                ProductModel.__table__,
                ProductTypeModel.schema_version,
                VariantModel.id.label("variant_id"),
                VariantModel.virtual,
                VariantModel.downloadable,
            )
            .join(ProductTypeModel, ProductTypeModel.id == ProductModel.product_type_id)
            .join(VariantModel, VariantModel.product_id == ProductModel.id)
        )
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
        """Проверяет принадлежность позиции в запросе двух идентичностей."""
        row = (
            (
                await self._session.execute(
                    select(
                        ProductModel.__table__,
                        ProductTypeModel.schema_version,
                        VariantModel.id.label("variant_id"),
                        VariantModel.virtual,
                        VariantModel.downloadable,
                    )
                    .join(
                        ProductTypeModel,
                        ProductTypeModel.id == ProductModel.product_type_id,
                    )
                    .join(VariantModel, VariantModel.product_id == ProductModel.id)
                    .where(
                        ProductModel.id == product_id.uuid,
                        VariantModel.id == variant_id.uuid,
                    )
                )
            )
            .mappings()
            .one_or_none()
        )
        return (
            None
            if row is None
            else ProductQueryMapper.to_variant(await self._projection(row), locale)
        )

    async def _projection(self, row: Mapping[str, Any]) -> dict[str, Any]:
        """Собирает read-значения из структурированных таблиц без восстановления агрегата."""
        return {
            **row,
            "translations": await read_product_translations(self._session, row["id"]),
            "variant_translations": await read_variant_translations(
                self._session, row["variant_id"]
            ),
        }
