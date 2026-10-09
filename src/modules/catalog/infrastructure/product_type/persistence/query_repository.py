from typing import Any
from collections.abc import Mapping
from src.modules.catalog.infrastructure.persistence.models.content_block_translation import (
    ContentBlockTranslationModel,
)
from src.modules.catalog.infrastructure.persistence.models.product_type_translation import (
    ProductTypeTranslationModel,
)
from src.modules.catalog.infrastructure.product_type.persistence.product_type_translations import (
    read_product_type_translations,
)
from sqlalchemy import select, func, or_, cast, String
from sqlalchemy.ext.asyncio import AsyncSession
from src.modules.catalog.domain.product_type.value_object.identifier import (
    ProductTypeIdVO,
)
from src.modules.catalog.infrastructure.product_type.persistence.query_mapper import (
    ProductTypeQueryMapper,
)
from src.modules.catalog.infrastructure.persistence.models.product_type import (
    ProductTypeModel,
)
from src.modules.catalog.infrastructure.persistence.models.content_block import (
    ContentBlockModel,
)
from src.modules.catalog.infrastructure.persistence.models.product_type_block import (
    ProductTypeBlockModel,
)
from src.modules.catalog.application.product_type.query.get_product_type.dto import (
    GetProductTypeDetailsDTO,
)
from src.modules.catalog.application.product_type.query.list_product_types.dto import (
    ListProductTypesPageDTO,
)


class SqlAlchemyProductTypeQueryRepository:
    """Читает SQL-проекции в уже выбранной tenant-схеме."""

    def __init__(self, session: AsyncSession) -> None:
        """Получает сессию внешнего UoW."""
        self._session = session

    async def get_details(
        self, identifier: ProductTypeIdVO, locale: str
    ) -> GetProductTypeDetailsDTO | None:
        """Возвращает карточку и null при отсутствии перевода выбранной locale."""
        row = (
            (
                await self._session.execute(
                    select(ProductTypeModel.__table__).where(
                        ProductTypeModel.id == identifier.uuid
                    )
                )
            )
            .mappings()
            .one_or_none()
        )
        if row is None:
            return None
        return ProductTypeQueryMapper.to_details(
            await self._projection(row), locale, await self._blocks(identifier, locale)
        )

    async def list_page(
        self, locale: str, search: str, page: int, page_size: int
    ) -> ListProductTypesPageDTO:
        """Читает страницу и total с одинаковыми серверными фильтрами."""
        statement = select(ProductTypeModel.__table__)
        if search:
            escaped = (
                search.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            )
            statement = statement.where(
                or_(
                    select(ProductTypeTranslationModel.product_type_id)
                    .where(
                        ProductTypeTranslationModel.product_type_id
                        == ProductTypeModel.id,
                        ProductTypeTranslationModel.locale == locale,
                        ProductTypeTranslationModel.label.ilike(
                            "%" + escaped + "%", escape="\\"
                        ),
                    )
                    .exists()
                    | ProductTypeModel.code.ilike("%" + escaped + "%", escape="\\"),
                    cast(ProductTypeModel.id, String).ilike(
                        "%" + escaped + "%", escape="\\"
                    ),
                )
            )
        total = await self._session.scalar(
            select(func.count()).select_from(statement.subquery())
        )
        rows = (
            (
                await self._session.execute(
                    statement.order_by(
                        ProductTypeModel.created_at.desc(), ProductTypeModel.id
                    )
                    .offset((page - 1) * page_size)
                    .limit(page_size)
                )
            )
            .mappings()
            .all()
        )
        items = tuple(
            [
                ProductTypeQueryMapper.to_list_item(
                    await self._projection(row),
                    locale,
                    await self._blocks(ProductTypeIdVO(row["id"]), locale),
                )
                for row in rows
            ]
        )
        return ListProductTypesPageDTO(items, total or 0, page, page_size)

    async def _blocks(
        self, identifier: ProductTypeIdVO, locale: str
    ) -> tuple[Mapping[str, Any], ...]:
        """Читает связи и определения непосредственно в проекцию редактора."""
        links = ProductTypeBlockModel.__table__
        rows = (
            (
                await self._session.execute(
                    select(
                        links,
                        ContentBlockModel.code,
                        ContentBlockModel.value_type,
                        ContentBlockTranslationModel.label,
                    )
                    .join(
                        ContentBlockModel,
                        ContentBlockModel.id == ProductTypeBlockModel.block_id,
                    )
                    .outerjoin(
                        ContentBlockTranslationModel,
                        (
                            ContentBlockTranslationModel.content_block_id
                            == ContentBlockModel.id
                        )
                        & (ContentBlockTranslationModel.locale == locale),
                    )
                    .where(ProductTypeBlockModel.product_type_id == identifier.uuid)
                    .order_by(
                        ProductTypeBlockModel.scope, ProductTypeBlockModel.position
                    )
                )
            )
            .mappings()
            .all()
        )
        return tuple(rows)

    async def _projection(self, row: Mapping[str, Any]) -> dict[str, Any]:
        """Собирает read-значения из структурированных таблиц без восстановления агрегата."""
        return {
            **row,
            "translations": await read_product_type_translations(
                self._session, row["id"]
            ),
        }
