from datetime import datetime
from sqlalchemy import select, delete
from src.modules.price_lists.domain.price_list.entity import PriceList
from src.modules.price_lists.domain.price_list.value_object import PriceListIdVO
from src.modules.price_lists.domain.sync_run.value_object import SyncRunIdVO
from src.modules.price_lists.domain.price_list.error import PriceListNotFoundError
from src.modules.price_lists.infrastructure.persistence.models import PriceListModel
from src.modules.price_lists.infrastructure.persistence.base import (
    SessionRepository,
    checked,
    identifier,
    entity_values,
)


def price_list_entity(row):
    """Явно мапит tenant price-list row в aggregate."""
    values = {}
    for name in PriceList.__dataclass_fields__:
        value = row[name]
        if name == "id":
            value = identifier(value, PriceListIdVO)
        elif name in ("created_by", "updated_by"):
            value = identifier(value)
        elif name == "last_sync_run_id":
            value = identifier(value, SyncRunIdVO, optional=True)
        elif name in ("created_at", "updated_at"):
            value = checked(value, datetime)
        elif name.endswith("_at"):
            value = checked(value, datetime, optional=True)
        elif name in ("mapping_version", "missing_threshold", "schedule_revision"):
            value = checked(value, int)
        elif name in ("source_config", "mapping_config"):
            value = dict(checked(value, dict))
        else:
            value = checked(
                value, str, optional=name in ("source_preset", "cron_expression")
            )
        values[name] = value
    return PriceList(**values)


class SqlAlchemyPriceListRepository(SessionRepository):
    """Реализует command repository прайса на текущей UoW session."""

    async def get(self, tenant_id, price_list_id, *, for_update=False):
        """Читает aggregate текущего tenant и проверяет его наличие."""
        table = PriceListModel.__table__
        statement = select(table).where(table.c.id == price_list_id.uuid)
        if for_update:
            # Lifecycle must remain writable while publication holds FK KEY SHARE locks.
            statement = statement.with_for_update(key_share=True)
        result = await self.session.execute(
            statement.execution_options(**self.execution_options(tenant_id))
        )
        row = result.mappings().one_or_none()
        if row is None:
            raise PriceListNotFoundError("Price list not found.")
        return price_list_entity(row)

    async def add(self, tenant_id, price_list):
        """Сохраняет созданный aggregate, включая внешне назначенный id."""
        await self.insert_many(
            tenant_id, PriceListModel.__table__, [entity_values(price_list)]
        )

    async def save(self, tenant_id, price_list):
        """Сохраняет бизнес-изменения с entity audit timestamps."""
        await self.update_many(
            tenant_id, PriceListModel.__table__, [entity_values(price_list)]
        )

    async def delete(self, tenant_id, price_list_id):
        """Удаляет aggregate текущего tenant."""
        table = PriceListModel.__table__
        result = await self.session.execute(
            delete(table)
            .where(table.c.id == price_list_id.uuid)
            .execution_options(**self.execution_options(tenant_id))
        )
        if not result.rowcount:
            raise PriceListNotFoundError("Price list not found.")


__all__ = ["SqlAlchemyPriceListRepository", "price_list_entity"]
