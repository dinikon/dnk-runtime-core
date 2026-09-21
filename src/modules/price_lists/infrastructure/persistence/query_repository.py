from datetime import datetime
from decimal import Decimal
from sqlalchemy import select, func, case, and_, or_, literal_column
from src.modules.price_lists.infrastructure.persistence.base import (
    SessionRepository,
    checked,
    identifier,
)
from src.modules.price_lists.infrastructure.persistence.models import (
    PriceListModel,
    PartnerOfferModel,
    PartnerOfferStateModel,
    PriceListSyncRunModel,
)
from src.modules.price_lists.infrastructure.persistence.price_list_repository import (
    price_list_entity,
)
from src.modules.price_lists.infrastructure.persistence.sync_run_repository import (
    sync_run_entity,
)
from src.modules.price_lists.infrastructure.persistence.pagination import (
    cursor_clause,
    encode_cursor,
)
from src.modules.price_lists.application.price_list.dto.price_list_dto import (
    PriceListDTO,
    PriceListListItemDTO,
)
from src.modules.price_lists.application.offer.dto.offer_dto import (
    OfferDTO,
    OfferStateDTO,
    OfferPageDTO,
)
from src.modules.price_lists.application.sync_run.dto.sync_run_dto import SyncRunDTO
from src.modules.price_lists.domain.offer.value_object import OfferIdVO, OfferStateIdVO
from src.modules.price_lists.domain.price_list.value_object import PriceListIdVO
from src.modules.price_lists.domain.sync_run.value_object import SyncRunIdVO
from src.modules.shared.application.pagination.errors import InvalidCursorError


class SqlAlchemyPriceListQueryRepository(SessionRepository):
    """Typed query adapter с совместимым offset и keyset режимом."""

    async def list(self, tenant_id, *, scope="current"):
        """Возвращает DTO прайсов выбранного tenant и scope."""
        table = PriceListModel.__table__
        offers = PartnerOfferModel.__table__
        runs = PriceListSyncRunModel.__table__
        active_offer_count = (
            select(func.count())
            .where(offers.c.price_list_id == table.c.id)
            .where(offers.c.lifecycle_status == "active")
            .correlate(table)
            .scalar_subquery()
        )
        last_run_status = (
            select(runs.c.status)
            .where(runs.c.id == table.c.last_sync_run_id)
            .correlate(table)
            .scalar_subquery()
        )
        statement = select(
            table,
            active_offer_count.label("active_offer_count"),
            last_run_status.label("last_run_status"),
        )
        if scope == "current":
            statement = statement.where(table.c.status != "archived")
        elif scope == "archived":
            statement = statement.where(table.c.status == "archived")
        result = await self.session.execute(
            statement.order_by(table.c.created_at.desc(), table.c.id).execution_options(
                **self.execution_options(tenant_id)
            )
        )
        return [
            PriceListListItemDTO(
                **{
                    name: getattr(entity, name)
                    for name in PriceListDTO.__dataclass_fields__
                },
                active_offer_count=int(row["active_offer_count"]),
                last_run_status=checked(row["last_run_status"], str, optional=True),
            )
            for row in result.mappings()
            for entity in [price_list_entity(row)]
        ]

    async def list_runs(self, query):
        """Читает ограниченную историю запусков прайса."""
        table = PriceListSyncRunModel.__table__
        result = await self.session.execute(
            select(table)
            .where(table.c.price_list_id == query.price_list_id.uuid)
            .order_by(table.c.started_at.desc(), table.c.id)
            .limit(100)
            .execution_options(**self.execution_options(query.tenant_id))
        )
        return [
            SyncRunDTO(
                **{
                    name: getattr(entity, name)
                    for name in SyncRunDTO.__dataclass_fields__
                }
            )
            for row in result.mappings()
            for entity in [sync_run_entity(row)]
        ]

    async def list_offers(self, query):
        """Читает текущие предложения с серверными фильтрами."""
        filters = query.filters
        include_archived = query.include_archived
        offers = PartnerOfferModel.__table__
        states = PartnerOfferStateModel.__table__
        price_lists = PriceListModel.__table__
        income = states.c.rrp - states.c.purchase_price
        margin = case((states.c.rrp > 0, income / states.c.rrp * 100), else_=None)
        base = (
            select(
                offers.c.id,
                offers.c.sku,
                offers.c.external_id,
                offers.c.title,
                offers.c.lifecycle_status,
                offers.c.price_list_id,
                price_lists.c.title.label("price_list_title"),
                states.c.purchase_price,
                states.c.rrp,
                states.c.currency,
                states.c.availability,
                states.c.quantity,
                states.c.observed_at,
                income.label("recommended_retail_income"),
                margin.label("margin_percent"),
            )
            .join(price_lists, price_lists.c.id == offers.c.price_list_id)
            .join(states, states.c.id == offers.c.current_state_id, isouter=True)
        )
        clauses = []
        if not include_archived:
            clauses.append(price_lists.c.status != "archived")
        if filters.get("price_list_ids"):
            clauses.append(
                offers.c.price_list_id.in_(
                    [value.uuid for value in filters["price_list_ids"]]
                )
            )
        if filters.get("availability"):
            clauses.append(states.c.availability.in_(filters["availability"]))
        for key, expression in {
            "purchase_price": states.c.purchase_price,
            "recommended_retail_income": income,
            "margin_percent": margin,
        }.items():
            if filters.get(f"{key}_min") is not None:
                clauses.append(expression >= filters[f"{key}_min"])
            if filters.get(f"{key}_max") is not None:
                clauses.append(expression <= filters[f"{key}_max"])
        if filters.get("has_rrp") is True:
            clauses.append(states.c.rrp.is_not(None))
        elif filters.get("has_rrp") is False:
            clauses.append(states.c.rrp.is_(None))
        q = str(filters.get("q") or "").strip()
        if q:
            pattern = f"%{q}%"
            empty = literal_column("''")
            separator = literal_column("' '")
            document = func.to_tsvector(
                literal_column("'simple'"),
                func.coalesce(offers.c.title, empty)
                + separator
                + func.coalesce(offers.c.sku, empty)
                + separator
                + func.coalesce(offers.c.external_id, empty),
            )
            search_query = func.plainto_tsquery(literal_column("'simple'"), q)
            clauses.append(
                or_(
                    document.op("@@")(search_query),
                    price_lists.c.title.ilike(pattern),
                )
            )
        if clauses:
            base = base.where(and_(*clauses))
        sort_columns = {
            "title": offers.c.title,
            "sku": offers.c.sku,
            "purchase_price": states.c.purchase_price,
            "rrp": states.c.rrp,
            "recommended_retail_income": income,
            "margin_percent": margin,
            "availability": states.c.availability,
            "observed_at": states.c.observed_at,
        }
        return await self.page(
            query, base, sort_columns, offers.c.id, "offers", OfferDTO
        )

    async def offer_history(self, query):
        """Читает историю без OFFSET в cursor режиме."""
        filters = query.filters
        states = PartnerOfferStateModel.__table__
        income = states.c.rrp - states.c.purchase_price
        margin = case((states.c.rrp > 0, income / states.c.rrp * 100), else_=None)
        base = select(
            states,
            income.label("recommended_retail_income"),
            margin.label("margin_percent"),
        ).where(states.c.offer_id == query.offer_id.uuid)
        clauses = []
        if filters.get("observed_from") is not None:
            clauses.append(states.c.observed_at >= filters["observed_from"])
        if filters.get("observed_to") is not None:
            clauses.append(states.c.observed_at <= filters["observed_to"])
        for key, expression in {
            "purchase_price": states.c.purchase_price,
            "rrp": states.c.rrp,
            "recommended_retail_income": income,
            "margin_percent": margin,
            "quantity": states.c.quantity,
        }.items():
            if filters.get(f"{key}_min") is not None:
                clauses.append(expression >= filters[f"{key}_min"])
            if filters.get(f"{key}_max") is not None:
                clauses.append(expression <= filters[f"{key}_max"])
        if filters.get("availability"):
            clauses.append(states.c.availability.in_(filters["availability"]))
        if filters.get("change_reason"):
            clauses.append(states.c.change_reason.in_(filters["change_reason"]))
        if clauses:
            base = base.where(and_(*clauses))
        sort_columns = {
            "observed_at": states.c.observed_at,
            "purchase_price": states.c.purchase_price,
            "rrp": states.c.rrp,
            "recommended_retail_income": income,
            "margin_percent": margin,
            "quantity": states.c.quantity,
        }
        return await self.page(
            query,
            base,
            sort_columns,
            states.c.id,
            "history:" + str(query.offer_id),
            OfferStateDTO,
        )

    async def page(self, query, base, sort_columns, id_column, scope, dto_class):
        """Ограничивает страницу до агрегации change_count."""
        if query.sort not in sort_columns:
            raise InvalidCursorError("Unknown sort column.")
        expression = sort_columns[query.sort]
        clause = cursor_clause(query, scope, expression, id_column)
        options = self.execution_options(query.tenant_id)
        total = None
        if query.pagination == "offset" or query.include_total:
            total = int(
                await self.session.scalar(
                    select(func.count())
                    .select_from(base.subquery())
                    .execution_options(**options)
                )
            )
        if clause is not None:
            base = base.where(clause)
        order = expression.asc() if query.direction == "asc" else expression.desc()
        statement = (
            base.add_columns(expression.label("_cursor_value"))
            .order_by(order.nulls_last(), id_column.asc())
            .limit(query.limit + (query.pagination == "cursor"))
        )
        if query.pagination == "offset":
            statement = statement.offset(query.offset)
        result = await self.session.execute(statement.execution_options(**options))
        rows = list(result.mappings())
        has_more = len(rows) > query.limit
        rows = rows[: query.limit]
        changes = {}
        if dto_class is OfferDTO and rows:
            table = PartnerOfferStateModel.__table__
            result = await self.session.execute(
                select(table.c.offer_id, func.count().label("count"))
                .where(
                    table.c.offer_id.in_([row["id"] for row in rows]),
                    table.c.change_reason != "initial",
                )
                .group_by(table.c.offer_id)
                .execution_options(**options)
            )
            changes = {row.offer_id: int(row.count) for row in result}
        items = []
        for row in rows:
            values = {}
            for name in dto_class.__dataclass_fields__:
                if name in (
                    "historical_conversion",
                    "current_conversion",
                    "display_conversion",
                ):
                    continue
                if name == "change_count":
                    values[name] = changes.get(row["id"], 0)
                    continue
                value = row[name]
                if name == "id":
                    value = identifier(
                        value, OfferIdVO if dto_class is OfferDTO else OfferStateIdVO
                    )
                elif name == "price_list_id":
                    value = identifier(value, PriceListIdVO)
                elif name == "offer_id":
                    value = identifier(value, OfferIdVO)
                elif name == "sync_run_id":
                    value = identifier(value, SyncRunIdVO)
                elif name == "observed_at":
                    value = checked(value, datetime, optional=True)
                elif name == "quantity":
                    value = checked(value, int, optional=True)
                elif name in (
                    "purchase_price",
                    "rrp",
                    "recommended_retail_income",
                    "margin_percent",
                ):
                    value = checked(value, Decimal, optional=True)
                else:
                    value = checked(
                        value, str, optional=name in ("currency", "availability")
                    )
                values[name] = value
            items.append(dto_class(**values))
        cursor = (
            encode_cursor(query, scope, rows[-1]["_cursor_value"], rows[-1]["id"])
            if has_more and rows
            else None
        )
        return OfferPageDTO(
            items, total, query.offset, query.limit, query.pagination, cursor, has_more
        )


__all__ = ["SqlAlchemyPriceListQueryRepository"]
