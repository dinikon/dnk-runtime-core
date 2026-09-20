from datetime import datetime
from decimal import Decimal
from sqlalchemy import select, delete, update, tuple_, or_, and_
from sqlalchemy.exc import IntegrityError
from src.modules.price_lists.infrastructure.persistence.base import (
    SessionRepository,
    checked,
)
from src.modules.price_lists.infrastructure.persistence.models import (
    PriceListSyncItemModel,
    PriceListSyncRunModel,
)
from src.modules.price_lists.application.sync_run.dto.parsed_row_dto import ParsedRow
from src.modules.price_lists.domain.sync_run.error import DuplicateExternalIdError


class SqlAlchemyStagingRepository(SessionRepository):
    """Staging с DB-дедупликацией и ограниченными SQL операциями."""

    async def append(self, tenant_id, run_id, rows):
        """Пишет пакет; ошибочные поля не попадают в типизированные колонки."""
        records = []
        for row in rows:
            value = row.normalized
            record = dict(
                sync_run_id=run_id.uuid,
                row_number=row.row_number,
                external_id=(
                    str(value["external_id"])
                    if value.get("external_id") is not None
                    and 1 <= len(str(value["external_id"])) <= 255
                    else None
                ),
                validation_errors=list(row.errors),
                quarantined=False,
            )
            for key in (
                "sku",
                "title",
                "purchase_price",
                "rrp",
                "currency",
                "availability",
                "quantity",
                "value_hash",
            ):
                record[key] = None if row.errors else value.get(key)
            record["normalized_payload"] = (
                {
                    key: str(v)[:512] if v is not None else None
                    for key, v in value.items()
                    if key
                    in (
                        "external_id",
                        "sku",
                        "title",
                        "purchase_price",
                        "rrp",
                        "currency",
                        "availability",
                        "quantity",
                    )
                }
                if row.errors
                else {}
            )
            records.append(record)
        try:
            await self.insert_many(tenant_id, PriceListSyncItemModel.__table__, records)
        except Exception as exc:
            if getattr(exc,"constraint_name",None)=="uq_sync_item_external_id" or (isinstance(exc,IntegrityError) and "uq_sync_item_external_id" in str(exc.orig)):
                raise DuplicateExternalIdError(
                    "Source contains duplicate external_id values."
                ) from None
            raise

    async def read_batch(self, tenant_id, run_id, after, limit):
        """Keyset-чтение нормализованных строк в DTO."""
        table = PriceListSyncItemModel.__table__
        result = await self.session.execute(
            select(table)
            .where(table.c.sync_run_id == run_id.uuid, table.c.row_number > after)
            .order_by(table.c.row_number)
            .limit(min(limit, self.read_limit))
            .execution_options(**self.execution_options(tenant_id))
        )
        rows = []
        for row in result.mappings():
            errors = tuple(
                checked(error, str) for error in checked(row["validation_errors"], list)
            )
            normalized = (
                dict(checked(row["normalized_payload"], dict))
                if errors
                else {
                    key: checked(
                        row[key],
                        (
                            Decimal
                            if key in ("purchase_price", "rrp")
                            else int if key == "quantity" else str
                        ),
                        optional=key in ("rrp", "quantity"),
                    )
                    for key in (
                        "external_id",
                        "sku",
                        "title",
                        "purchase_price",
                        "rrp",
                        "currency",
                        "availability",
                        "quantity",
                        "value_hash",
                    )
                }
            )
            rows.append(ParsedRow(checked(row["row_number"], int), normalized, errors))
        return rows

    async def quarantine(self, tenant_id, run_id, external_ids):
        """Оставляет диагностику новых quarantine-предложений."""
        if not external_ids:
            return
        table = PriceListSyncItemModel.__table__
        for start in range(0, len(external_ids), self.read_limit):
            await self.session.execute(
                update(table)
                .where(
                    table.c.sync_run_id == run_id.uuid,
                    table.c.external_id.in_(
                        external_ids[start : start + self.read_limit]
                    ),
                )
                .values(quarantined=True)
                .execution_options(**self.execution_options(tenant_id))
            )

    async def delete_batch(self, tenant_id, run_id, *, keep_quarantine=False):
        """Удаляет не больше одного пакета выбранного запуска."""
        table = PriceListSyncItemModel.__table__
        selected = select(table.c.row_number).where(table.c.sync_run_id == run_id.uuid)
        if keep_quarantine:
            selected = selected.where(table.c.quarantined.is_(False))
        selected = selected.order_by(table.c.row_number).limit(self.read_limit)
        result = await self.session.execute(
            delete(table)
            .where(table.c.sync_run_id == run_id.uuid, table.c.row_number.in_(selected))
            .execution_options(**self.execution_options(tenant_id))
        )
        return int(result.rowcount or 0)

    async def cleanup_batch(self, tenant_id, older_than):
        """Удаляет старые failed и оставшиеся успешные staging пакеты."""
        table = PriceListSyncItemModel.__table__
        runs = PriceListSyncRunModel.__table__
        selected = (
            select(table.c.sync_run_id, table.c.row_number)
            .join(runs, runs.c.id == table.c.sync_run_id)
            .where(
                or_(
                    and_(
                        runs.c.status.in_(("failed", "skipped")),
                        runs.c.finished_at < older_than,
                    ),
                    and_(
                        runs.c.status.in_(("succeeded", "partial")),
                        table.c.quarantined.is_(False),
                    ),
                )
            )
            .order_by(table.c.sync_run_id, table.c.row_number)
            .limit(self.read_limit)
        )
        result = await self.session.execute(
            delete(table)
            .where(tuple_(table.c.sync_run_id, table.c.row_number).in_(selected))
            .execution_options(**self.execution_options(tenant_id))
        )
        return int(result.rowcount or 0)


__all__ = ["SqlAlchemyStagingRepository"]
