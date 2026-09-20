from datetime import datetime
from sqlalchemy import select, update
from src.modules.price_lists.domain.sync_run.entity import SyncRun
from src.modules.price_lists.domain.sync_run.value_object import SyncRunIdVO
from src.modules.price_lists.domain.price_list.value_object import PriceListIdVO
from src.modules.price_lists.infrastructure.persistence.base import (
    SessionRepository,
    checked,
    identifier,
    entity_values,
)
from src.modules.price_lists.infrastructure.persistence.models import (
    PriceListSyncRunModel,
)


def sync_run_entity(row):
    """Проверяет persistence типы запуска синхронизации."""
    values = {}
    for name in SyncRun.__dataclass_fields__:
        value = row[name]
        if name == "id":
            value = identifier(value, SyncRunIdVO)
        elif name == "price_list_id":
            value = identifier(value, PriceListIdVO)
        elif name == "scheduled_job_id":
            value = identifier(value, optional=True)
        elif name.endswith("_at"):
            value = checked(value, datetime, optional=name != "started_at")
        elif name == "counters":
            value = {
                checked(k, str): checked(v, int)
                for k, v in checked(value, dict).items()
            }
        else:
            value = checked(
                value, str, optional=name in ("source_checksum", "error_summary")
            )
        values[name] = value
    return SyncRun(**values)


class SqlAlchemySyncRunRepository(SessionRepository):
    """Repository прогресса и итогов синхронизации."""

    async def unfinished_batch(self, tenant_id, after):
        """Выбирает ограниченный пакет runs для восстановления после crash."""
        table = PriceListSyncRunModel.__table__
        statement = select(table).where(
            table.c.status.in_(("queued", "downloading", "parsing", "applying"))
        )
        if after is not None:
            statement = statement.where(table.c.id > after.uuid)
        result = await self.session.execute(
            statement.order_by(table.c.id)
            .limit(self.read_limit)
            .execution_options(**self.execution_options(tenant_id))
        )
        return [sync_run_entity(row) for row in result.mappings()]

    async def skip_running(self, tenant_id, price_list_id, now):
        """Фиксирует завершение активных runs при pause/archive."""
        table = PriceListSyncRunModel.__table__
        await self.session.execute(
            update(table)
            .where(
                table.c.price_list_id == price_list_id.uuid,
                table.c.status.in_(("queued", "downloading", "parsing", "applying")),
            )
            .values(
                status="skipped",
                finished_at=now,
                error_summary="Synchronization superseded by lifecycle change.",
            )
            .execution_options(**self.execution_options(tenant_id))
        )

    async def find_by_job(self, tenant_id, price_list_id, job_id):
        """Находит предыдущий запуск этой задачи для идемпотентного повтора."""
        table = PriceListSyncRunModel.__table__
        result = await self.session.execute(
            select(table)
            .where(
                table.c.price_list_id == price_list_id.uuid,
                table.c.scheduled_job_id == job_id.uuid,
            )
            .execution_options(**self.execution_options(tenant_id))
        )
        row = result.mappings().one_or_none()
        return sync_run_entity(row) if row is not None else None

    async def add(self, tenant_id, run):
        """Сохраняет новый запуск."""
        await self.insert_many(
            tenant_id, PriceListSyncRunModel.__table__, [entity_values(run)]
        )

    async def save(self, tenant_id, run):
        """Сохраняет прогресс в текущей транзакции."""
        await self.update_many(
            tenant_id, PriceListSyncRunModel.__table__, [entity_values(run)]
        )


__all__ = ["SqlAlchemySyncRunRepository", "sync_run_entity"]
