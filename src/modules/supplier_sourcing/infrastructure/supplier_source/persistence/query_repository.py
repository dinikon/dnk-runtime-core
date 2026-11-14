from uuid import UUID
from sqlalchemy import select, func, or_, Nullable
from sqlalchemy.orm import aliased
from sqlalchemy.sql.elements import ColumnElement
from sqlalchemy.ext.asyncio import AsyncSession
from src.modules.supplier_sourcing.infrastructure.persistence.models.supplier_source import (
    SupplierSourceModel,
)
from src.modules.supplier_sourcing.infrastructure.persistence.models.supplier_source_fulfillment_mode import (
    SupplierSourceFulfillmentModeModel,
)
from src.modules.supplier_sourcing.infrastructure.supplier_source.persistence.query_mapper import (
    SupplierSourceQueryMapper,
)
from src.modules.supplier_sourcing.application.supplier_source.query.get_supplier_source.query import (
    GetSupplierSourceQuery,
)
from src.modules.supplier_sourcing.application.supplier_source.query.get_supplier_source.dto import (
    GetSupplierSourceResultDTO,
)
from src.modules.supplier_sourcing.application.supplier_source.query.list_supplier_sources.query import (
    ListSupplierSourcesQuery,
)
from src.modules.supplier_sourcing.application.supplier_source.query.list_supplier_sources.dto import (
    ListSupplierSourcesResultDTO,
)


class SqlAlchemySupplierSourceQueryRepository:
    """Читает согласованные проекции карточек и режимов без размножения страницы."""

    def __init__(self, session: AsyncSession) -> None:
        """Принимает tenant-сессию общего UoW."""
        self._session = session

    async def get_details(
        self, query: GetSupplierSourceQuery
    ) -> GetSupplierSourceResultDTO | None:
        """Читает карточку и её режимы без восстановления агрегата."""
        statement = (
            select(SupplierSourceModel, Nullable(SupplierSourceFulfillmentModeModel))
            .outerjoin(
                SupplierSourceFulfillmentModeModel,
                SupplierSourceFulfillmentModeModel.supplier_source_id
                == SupplierSourceModel.id,
            )
            .where(SupplierSourceModel.id == query.source_id.uuid)
            .order_by(SupplierSourceFulfillmentModeModel.mode)
            .execution_options(populate_existing=True)
        )
        rows = (await self._session.execute(statement)).all()
        if not rows:
            return None
        return SupplierSourceQueryMapper.to_details(
            rows[0][0], tuple(mode for _, mode in rows if mode is not None)
        )

    async def list(
        self, query: ListSupplierSourcesQuery
    ) -> ListSupplierSourcesResultDTO:
        """Считает total и страницу по одним фильтрам, включая false и буквальный поиск."""
        conditions: list[ColumnElement[bool]] = []
        if query.search is not None:
            conditions.append(
                or_(
                    SupplierSourceModel.name.icontains(query.search, autoescape=True),
                    SupplierSourceModel.external_warehouse_code.icontains(
                        query.search, autoescape=True
                    ),
                )
            )
        if query.supplier_model_key is not None:
            conditions.append(
                SupplierSourceModel.supplier_model_key == query.supplier_model_key.value
            )
        if query.supplier_id is not None:
            conditions.append(SupplierSourceModel.supplier_id == query.supplier_id)
        if query.is_active is not None:
            conditions.append(SupplierSourceModel.is_active == query.is_active)
        if query.fulfillment_mode is not None:
            conditions.append(
                select(SupplierSourceFulfillmentModeModel.supplier_source_id)
                .where(
                    SupplierSourceFulfillmentModeModel.supplier_source_id
                    == SupplierSourceModel.id,
                    SupplierSourceFulfillmentModeModel.mode
                    == query.fulfillment_mode.value,
                )
                .exists()
            )
        filters: tuple[ColumnElement[bool], ...] = tuple(conditions)
        total = (
            await self._session.execute(
                select(func.count()).select_from(SupplierSourceModel).where(*filters)
            )
        ).scalar_one()
        page = (
            select(SupplierSourceModel)
            .where(*filters)
            .order_by(SupplierSourceModel.name, SupplierSourceModel.id)
            .offset(query.offset)
            .limit(query.limit)
            .subquery()
        )
        source = aliased(SupplierSourceModel, page)
        statement = (
            select(source, Nullable(SupplierSourceFulfillmentModeModel))
            .outerjoin(
                SupplierSourceFulfillmentModeModel,
                SupplierSourceFulfillmentModeModel.supplier_source_id == source.id,
            )
            .order_by(source.name, source.id, SupplierSourceFulfillmentModeModel.mode)
            .execution_options(populate_existing=True)
        )
        grouped: dict[
            UUID, tuple[SupplierSourceModel, list[SupplierSourceFulfillmentModeModel]]
        ] = {}
        for model, mode in (await self._session.execute(statement)).all():
            _, modes = grouped.setdefault(model.id, (model, []))
            if mode is not None:
                modes.append(mode)
        return ListSupplierSourcesResultDTO(
            items=tuple(
                SupplierSourceQueryMapper.to_list_item(model, modes)
                for model, modes in grouped.values()
            ),
            total=total,
            offset=query.offset,
            limit=query.limit,
        )
