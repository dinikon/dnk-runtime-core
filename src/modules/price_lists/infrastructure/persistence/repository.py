from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

import uuid6
from sqlalchemy import (
    and_,
    case,
    delete,
    func,
    insert,
    literal_column,
    or_,
    select,
    update,
)
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import dnk_config
from src.modules.price_lists.infrastructure.persistence.models import (
    PartnerOfferModel,
    PartnerOfferStateModel,
    PriceListModel,
    PriceListSyncItemModel,
    PriceListSyncRunModel,
)
from src.modules.price_lists.domain import canonical_state_hash
from src.modules.price_lists.infrastructure.source import ParsedRow
from src.modules.shared import EntityIdVO
from src.modules.shared.application.persistence.tenant_schema_naming import (
    TenantSchemaNaming,
)
from src.modules.shared.infrastructure.persistence.base import TENANT_SCHEMA_ALIAS

# Keep multi-row INSERT statements comfortably below asyncpg/PostgreSQL's
# 32,767 bind-parameter limit. The widest price-list row currently uses 13
# parameters, so a 1,000-row batch has at most 13,000 parameters.
PRICE_LIST_WRITE_BATCH_SIZE = 1_000


class SqlAlchemyPriceListRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.naming = TenantSchemaNaming(dnk_config.SCHEMA_PREFIX)

    def _options(self, tenant_id: UUID) -> dict[str, Any]:
        schema = self.naming.schema_name(EntityIdVO.from_value(tenant_id))
        return {"schema_translate_map": {TENANT_SCHEMA_ALIAS: schema}}

    async def _insert_many(
        self,
        *,
        tenant_id: UUID,
        table: sa.Table,
        values: list[dict[str, Any]],
    ) -> None:
        """Inserts large collections without exceeding driver bind limits."""
        for offset in range(0, len(values), PRICE_LIST_WRITE_BATCH_SIZE):
            batch = values[offset : offset + PRICE_LIST_WRITE_BATCH_SIZE]
            await self.session.execute(
                insert(table)
                .values(batch)
                .execution_options(**self._options(tenant_id))
            )

    async def create(
        self,
        *,
        tenant_id: UUID,
        actor_id: UUID,
        title: str,
        source_format: str,
        source_preset: str | None,
        source_url: str,
        source_url_display: str,
        source_config: dict[str, Any],
        mapping_config: dict[str, Any],
    ) -> UUID:
        price_list_id = uuid6.uuid7()
        await self.session.execute(
            insert(PriceListModel.__table__)
            .values(
                id=price_list_id,
                title=title,
                status="draft",
                source_format=source_format,
                source_preset=source_preset,
                source_url_secret=source_url,
                source_url_display=source_url_display,
                source_config=source_config,
                mapping_config=mapping_config,
                mapping_version=1,
                cron_expression=None,
                timezone="Europe/Kyiv",
                new_item_policy="create",
                missing_item_policy="mark_out_of_stock",
                missing_threshold=2,
                schedule_revision=1,
                created_by=actor_id,
                updated_by=actor_id,
            )
            .execution_options(**self._options(tenant_id))
        )
        return price_list_id

    async def get(self, tenant_id: UUID, price_list_id: UUID) -> dict[str, Any] | None:
        result = await self.session.execute(
            select(PriceListModel.__table__)
            .where(PriceListModel.__table__.c.id == price_list_id)
            .execution_options(**self._options(tenant_id))
        )
        row = result.mappings().one_or_none()
        return dict(row) if row else None

    async def list(self, tenant_id: UUID) -> list[dict[str, Any]]:
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
        result = await self.session.execute(
            select(
                table,
                active_offer_count.label("active_offer_count"),
                last_run_status.label("last_run_status"),
            )
            .order_by(table.c.created_at.desc(), table.c.id)
            .execution_options(**self._options(tenant_id))
        )
        return [dict(row) for row in result.mappings()]

    async def update_config(
        self,
        *,
        tenant_id: UUID,
        actor_id: UUID,
        price_list_id: UUID,
        values: dict[str, Any],
    ) -> bool:
        values = {**values, "updated_by": actor_id, "updated_at": datetime.now(UTC)}
        result = await self.session.execute(
            update(PriceListModel.__table__)
            .where(PriceListModel.__table__.c.id == price_list_id)
            .values(**values)
            .execution_options(**self._options(tenant_id))
        )
        return bool(result.rowcount)

    async def create_run(
        self,
        *,
        tenant_id: UUID,
        price_list_id: UUID,
        trigger: str,
        scheduled_job_id: UUID | None,
        planned_at: datetime | None,
    ) -> UUID:
        run_id = uuid6.uuid7()
        await self.session.execute(
            insert(PriceListSyncRunModel.__table__)
            .values(
                id=run_id,
                price_list_id=price_list_id,
                scheduled_job_id=scheduled_job_id,
                status="downloading",
                trigger=trigger,
                planned_at=planned_at,
                started_at=datetime.now(UTC),
                counters={},
            )
            .execution_options(**self._options(tenant_id))
        )
        return run_id

    async def get_run_by_job(
        self,
        *,
        tenant_id: UUID,
        price_list_id: UUID,
        scheduled_job_id: UUID,
    ) -> dict[str, Any] | None:
        runs = PriceListSyncRunModel.__table__
        result = await self.session.execute(
            select(runs)
            .where(runs.c.price_list_id == price_list_id)
            .where(runs.c.scheduled_job_id == scheduled_job_id)
            .execution_options(**self._options(tenant_id))
        )
        row = result.mappings().one_or_none()
        return dict(row) if row else None

    async def reset_run(self, *, tenant_id: UUID, run_id: UUID) -> None:
        """Prepares an interrupted/failed run for an idempotent retry."""
        runs = PriceListSyncRunModel.__table__
        staging = PriceListSyncItemModel.__table__
        await self.session.execute(
            delete(staging)
            .where(staging.c.sync_run_id == run_id)
            .execution_options(**self._options(tenant_id))
        )
        await self.session.execute(
            update(runs)
            .where(runs.c.id == run_id)
            .values(
                status="downloading",
                started_at=datetime.now(UTC),
                finished_at=None,
                source_checksum=None,
                counters={},
                error_summary=None,
            )
            .execution_options(**self._options(tenant_id))
        )

    async def finish_run(
        self,
        *,
        tenant_id: UUID,
        price_list_id: UUID,
        run_id: UUID,
        status: str,
        checksum: str | None,
        counters: dict[str, int],
        error: str | None = None,
    ) -> None:
        now = datetime.now(UTC)
        await self.session.execute(
            update(PriceListSyncRunModel.__table__)
            .where(PriceListSyncRunModel.__table__.c.id == run_id)
            .values(
                status=status,
                finished_at=now,
                source_checksum=checksum,
                counters=counters,
                error_summary=error,
            )
            .execution_options(**self._options(tenant_id))
        )
        price_values: dict[str, Any] = {"last_sync_run_id": run_id}
        if status in {"succeeded", "partial"}:
            price_values["last_success_at"] = now
        else:
            price_values["last_error_at"] = now
        await self.session.execute(
            update(PriceListModel.__table__)
            .where(PriceListModel.__table__.c.id == price_list_id)
            .values(**price_values)
            .execution_options(**self._options(tenant_id))
        )

    async def apply_rows(
        self,
        *,
        tenant_id: UUID,
        actor_id: UUID,
        price_list: dict[str, Any],
        run_id: UUID,
        rows: list[ParsedRow],
    ) -> dict[str, int]:
        now = datetime.now(UTC)
        valid = [row for row in rows if not row.errors]
        invalid = [row for row in rows if row.errors]
        seen_ids = {str(row.normalized["external_id"]) for row in valid}
        counters = {
            "read": len(rows),
            "valid": len(valid),
            "rejected": len(invalid),
            "created": 0,
            "changed": 0,
            "unchanged": 0,
            "missing": 0,
            "reappeared": 0,
            "ignored": 0,
            "quarantined": 0,
        }
        staging = PriceListSyncItemModel.__table__
        if rows:
            staging_values = [
                {
                    "sync_run_id": run_id,
                    "row_number": row.row_number,
                    "external_id": row.normalized.get("external_id"),
                    "sku": row.normalized.get("sku"),
                    "title": row.normalized.get("title"),
                    "purchase_price": row.normalized.get("purchase_price"),
                    "rrp": row.normalized.get("rrp"),
                    "currency": row.normalized.get("currency"),
                    "availability": row.normalized.get("availability"),
                    "quantity": row.normalized.get("quantity"),
                    "value_hash": row.normalized.get("value_hash"),
                    "normalized_payload": {
                        key: str(value) if isinstance(value, Decimal) else value
                        for key, value in row.normalized.items()
                    },
                    "validation_errors": list(row.errors),
                }
                for row in rows
            ]
            await self._insert_many(
                tenant_id=tenant_id,
                table=staging,
                values=staging_values,
            )
        offers = PartnerOfferModel.__table__
        states = PartnerOfferStateModel.__table__
        existing_result = await self.session.execute(
            select(offers)
            .where(offers.c.price_list_id == price_list["id"])
            .execution_options(**self._options(tenant_id))
        )
        existing = {row["external_id"]: dict(row) for row in existing_result.mappings()}
        current_states: dict[UUID, dict[str, Any]] = {}
        state_ids = [
            row["current_state_id"]
            for row in existing.values()
            if row["current_state_id"]
        ]
        if state_ids:
            state_result = await self.session.execute(
                select(states)
                .where(states.c.id.in_(state_ids))
                .execution_options(**self._options(tenant_id))
            )
            current_states = {row["id"]: dict(row) for row in state_result.mappings()}
        quarantined_ids: set[str] = set()
        for row in valid:
            value = row.normalized
            external_id = str(value["external_id"])
            offer = existing.get(external_id)
            reason = "source_change"
            if offer is None:
                new_policy = str(price_list.get("new_item_policy") or "create")
                if new_policy == "quarantine":
                    quarantined_ids.add(external_id)
                    counters["quarantined"] += 1
                    continue
                if new_policy == "ignore":
                    counters["ignored"] += 1
                    continue
                offer_id = uuid6.uuid7()
                await self.session.execute(
                    insert(offers)
                    .values(
                        id=offer_id,
                        price_list_id=price_list["id"],
                        sku=str(value["sku"]),
                        external_id=external_id,
                        title=str(value["title"]),
                        lifecycle_status="active",
                        current_state_id=None,
                        first_seen_at=now,
                        last_seen_at=now,
                        consecutive_missing_runs=0,
                        created_by=actor_id,
                        updated_by=actor_id,
                    )
                    .execution_options(**self._options(tenant_id))
                )
                counters["created"] += 1
                reason = "initial"
            else:
                offer_id = offer["id"]
                if offer["lifecycle_status"] in {"missing", "archived"}:
                    counters["reappeared"] += 1
                    reason = "reappeared"
                await self.session.execute(
                    update(offers)
                    .where(offers.c.id == offer_id)
                    .values(
                        sku=str(value["sku"]),
                        title=str(value["title"]),
                        lifecycle_status="active",
                        last_seen_at=now,
                        missing_since=None,
                        consecutive_missing_runs=0,
                        updated_by=actor_id,
                    )
                    .execution_options(**self._options(tenant_id))
                )
            current_state = (
                current_states.get(offer.get("current_state_id")) if offer else None
            )
            current_hash = current_state["value_hash"] if current_state else None
            if current_hash == value["value_hash"]:
                counters["unchanged"] += 1
                continue
            state_id = uuid6.uuid7()
            await self.session.execute(
                insert(states)
                .values(
                    id=state_id,
                    offer_id=offer_id,
                    sync_run_id=run_id,
                    observed_at=now,
                    purchase_price=value["purchase_price"],
                    rrp=value.get("rrp"),
                    currency=value["currency"],
                    availability=value["availability"],
                    quantity=value.get("quantity"),
                    value_hash=value["value_hash"],
                    change_reason=reason,
                )
                .execution_options(**self._options(tenant_id))
            )
            await self.session.execute(
                update(offers)
                .where(offers.c.id == offer_id)
                .values(current_state_id=state_id)
                .execution_options(**self._options(tenant_id))
            )
            counters["changed"] += 1
        missing_policy = str(
            price_list.get("missing_item_policy") or "mark_out_of_stock"
        )
        if existing:
            for external_id, offer in existing.items():
                if external_id in seen_ids:
                    continue
                missing_runs = int(offer["consecutive_missing_runs"] or 0) + 1
                lifecycle = offer["lifecycle_status"]
                if missing_runs >= int(price_list.get("missing_threshold") or 1):
                    if missing_policy == "mark_missing":
                        lifecycle = "missing"
                    elif missing_policy == "archive":
                        lifecycle = "archived"
                    elif missing_policy == "mark_out_of_stock":
                        lifecycle = "active"
                        current_state = current_states.get(offer["current_state_id"])
                        if current_state:
                            missing_hash = canonical_state_hash(
                                purchase_price=current_state["purchase_price"],
                                rrp=current_state["rrp"],
                                currency=current_state["currency"],
                                availability="out_of_stock",
                                quantity=0,
                            )
                            if current_state["value_hash"] != missing_hash:
                                state_id = uuid6.uuid7()
                                await self.session.execute(
                                    insert(states)
                                    .values(
                                        id=state_id,
                                        offer_id=offer["id"],
                                        sync_run_id=run_id,
                                        observed_at=now,
                                        purchase_price=current_state["purchase_price"],
                                        rrp=current_state["rrp"],
                                        currency=current_state["currency"],
                                        availability="out_of_stock",
                                        quantity=0,
                                        value_hash=missing_hash,
                                        change_reason="missing_policy",
                                    )
                                    .execution_options(**self._options(tenant_id))
                                )
                                await self.session.execute(
                                    update(offers)
                                    .where(offers.c.id == offer["id"])
                                    .values(current_state_id=state_id)
                                    .execution_options(**self._options(tenant_id))
                                )
                                counters["changed"] += 1
                    counters["missing"] += 1
                await self.session.execute(
                    update(offers)
                    .where(offers.c.id == offer["id"])
                    .values(
                        lifecycle_status=lifecycle,
                        consecutive_missing_runs=missing_runs,
                        missing_since=offer["missing_since"] or now,
                        updated_by=actor_id,
                    )
                    .execution_options(**self._options(tenant_id))
                )
        cleanup = delete(staging).where(staging.c.sync_run_id == run_id)
        if quarantined_ids:
            cleanup = cleanup.where(staging.c.external_id.not_in(quarantined_ids))
        await self.session.execute(
            cleanup.execution_options(**self._options(tenant_id))
        )
        return counters

    async def list_runs(
        self, tenant_id: UUID, price_list_id: UUID
    ) -> list[dict[str, Any]]:
        runs = PriceListSyncRunModel.__table__
        result = await self.session.execute(
            select(runs)
            .where(runs.c.price_list_id == price_list_id)
            .order_by(runs.c.started_at.desc())
            .limit(100)
            .execution_options(**self._options(tenant_id))
        )
        return [dict(row) for row in result.mappings()]

    async def list_offers(
        self,
        *,
        tenant_id: UUID,
        filters: dict[str, Any],
        offset: int,
        limit: int,
        sort: str,
        direction: str,
    ) -> tuple[list[dict[str, Any]], int]:
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
        if filters.get("price_list_ids"):
            clauses.append(offers.c.price_list_id.in_(filters["price_list_ids"]))
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
        count_result = await self.session.execute(
            select(func.count())
            .select_from(base.subquery())
            .execution_options(**self._options(tenant_id))
        )
        total = int(count_result.scalar_one())
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
        order = sort_columns.get(sort, states.c.observed_at)
        order = order.asc() if direction == "asc" else order.desc()
        result = await self.session.execute(
            base.order_by(order.nulls_last(), offers.c.id)
            .offset(offset)
            .limit(limit)
            .execution_options(**self._options(tenant_id))
        )
        return [dict(row) for row in result.mappings()], total

    async def offer_history(
        self, tenant_id: UUID, offer_id: UUID
    ) -> list[dict[str, Any]]:
        states = PartnerOfferStateModel.__table__
        income = states.c.rrp - states.c.purchase_price
        margin = case((states.c.rrp > 0, income / states.c.rrp * 100), else_=None)
        result = await self.session.execute(
            select(
                states,
                income.label("recommended_retail_income"),
                margin.label("margin_percent"),
            )
            .where(states.c.offer_id == offer_id)
            .order_by(states.c.observed_at.desc())
            .limit(500)
            .execution_options(**self._options(tenant_id))
        )
        return [dict(row) for row in result.mappings()]

    async def cleanup_failed_staging(
        self, *, tenant_id: UUID, older_than: datetime
    ) -> int:
        staging = PriceListSyncItemModel.__table__
        runs = PriceListSyncRunModel.__table__
        failed_runs = select(runs.c.id).where(
            runs.c.status == "failed",
            runs.c.finished_at.is_not(None),
            runs.c.finished_at < older_than,
        )
        result = await self.session.execute(
            delete(staging)
            .where(staging.c.sync_run_id.in_(failed_runs))
            .execution_options(**self._options(tenant_id))
        )
        return int(result.rowcount or 0)
