from sqlalchemy import func, bindparam
from sqlalchemy.dialects.postgresql import JSONB
import json
from sqlalchemy import text, JSON
from collections import defaultdict
from dataclasses import fields
from datetime import datetime
from decimal import Decimal
from uuid import UUID
from sqlalchemy import insert, update, column, cast, values as sql_values
from sqlalchemy.ext.asyncio import AsyncSession
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.shared.application.persistence.tenant_schema_naming import (
    TenantSchemaNaming,
)
from src.modules.shared.infrastructure.persistence.base import TENANT_SCHEMA_ALIAS
from src.modules.price_lists.application.sync_run.options import ImportOptions


class PersistenceMappingError(RuntimeError):
    """Тип сохранённого значения не соответствует контракту."""


def checked(value, expected, *, optional=False):
    """Проверяет persistence primitives до передачи в domain/application."""
    if optional and value is None:
        return None
    if not isinstance(value, expected) or (expected is int and isinstance(value, bool)):
        raise PersistenceMappingError("Unexpected persisted value type.")
    if expected is datetime and value.tzinfo is None:
        raise PersistenceMappingError("Persisted timestamp must have a timezone.")
    return value


def identifier(value, cls=EntityIdVO, *, optional=False):
    """Явно преобразует поддержанные UUID representations."""
    if optional and value is None:
        return None
    if not isinstance(value, (UUID, str)):
        raise PersistenceMappingError("Invalid persisted identifier.")
    return cls.from_value(value)


def entity_values(entity):
    """Преобразует поля entity в persistence primitives."""
    return {
        field.name: (
            value.uuid
            if isinstance(value := getattr(entity, field.name), EntityIdVO)
            else value
        )
        for field in fields(entity)
    }


class SessionRepository:
    """Общий tenant scope и ограниченные bulk statements."""

    def __init__(
        self, session: AsyncSession, naming: TenantSchemaNaming, options: ImportOptions
    ):
        self.session = session
        self.naming = naming
        self.options = options

    def execution_options(self, tenant_id: EntityIdVO):
        """Вычисляет schema для каждого вызова, не сохраняя tenant."""
        return {
            "schema_translate_map": {
                TENANT_SCHEMA_ALIAS: self.naming.schema_name(tenant_id)
            }
        }

    @property
    def read_limit(self):
        """Ограничивает также память одного materialized SQL результата."""
        return min(
            self.options.batch_size, max(1, self.options.batch_max_bytes // 4096), 2000
        )

    async def insert_many(self, tenant_id, table, records):
        """Делит INSERT по настройке и bind budget драйвера."""
        if not records:
            return
        if (
            self.session.bind.dialect.name == "postgresql"
            and self.session.bind.dialect.driver == "asyncpg"
        ):
            # Start the physical transaction before bypassing the SQLAlchemy
            # statement compiler; COPY remains covered by the shared UoW rollback.
            connection = await self.session.connection()
            await connection.execute(text("SELECT 1"))
            raw = await connection.get_raw_connection()
            columns = tuple(records[0])
            json_columns = {
                name for name in columns if isinstance(table.c[name].type, JSON)
            }
            for start in range(0, len(records), self.options.batch_size):
                batch = [
                    tuple(
                        (
                            json.dumps(row[name], ensure_ascii=False)
                            if name in json_columns and row[name] is not None
                            else row[name]
                        )
                        for name in columns
                    )
                    for row in records[start : start + self.options.batch_size]
                ]
                await raw.driver_connection.copy_records_to_table(
                    table.name,
                    schema_name=self.naming.schema_name(tenant_id),
                    columns=columns,
                    records=batch,
                )
            return
        width = len(records[0])
        limit = min(self.options.batch_size, max(1, 32000 // width))
        for start in range(0, len(records), limit):
            await self.session.execute(
                insert(table)
                .values(records[start : start + limit])
                .execution_options(**self.execution_options(tenant_id))
            )

    async def update_many(self, tenant_id, table, records):
        """Обновляет пакет через UPDATE FROM VALUES с явными типами."""
        if records and self.session.bind.dialect.name == "postgresql":
            # PostgreSQL's cached generic plan can retain a sequential UPDATE
            # scan chosen before the first import populated the table. Replan
            # these bounded writes against its current physical size.
            await self.session.connection()
            transaction = self.session.get_transaction()
            if (
                self.session.info.get("price_lists_custom_plan_transaction")
                is not transaction
            ):
                await self.session.execute(
                    text("SET LOCAL plan_cache_mode = force_custom_plan")
                )
                self.session.info["price_lists_custom_plan_transaction"] = transaction
        groups = defaultdict(list)
        for record in records:
            groups[tuple(sorted(k for k in record if k != "id"))].append(record)
        for names, items in groups.items():
            keys = ("id", *names)
            if self.session.bind.dialect.name == "postgresql":
                changed = (
                    func.jsonb_to_recordset(bindparam("records", type_=JSONB))
                    .table_valued(*(column(key, table.c[key].type) for key in keys))
                    .render_derived(name="changed", with_types=True)
                )
                statement = (
                    update(table)
                    .where(table.c.id == changed.c.id)
                    .values({key: changed.c[key] for key in names})
                    .execution_options(**self.execution_options(tenant_id))
                )
                for start in range(0, len(items), self.options.batch_size):
                    records = [
                        {
                            key: (
                                str(value)
                                if isinstance(value, (UUID, datetime, Decimal))
                                else value
                            )
                            for key, value in row.items()
                        }
                        for row in items[start : start + self.options.batch_size]
                    ]
                    await self.session.execute(statement, {"records": records})
                continue

            limit = min(self.options.batch_size, max(1, 32000 // len(keys)))
            for start in range(0, len(items), limit):
                changed = sql_values(
                    *(column(key, table.c[key].type) for key in keys), name="changed"
                ).data(
                    [
                        tuple(row[key] for key in keys)
                        for row in items[start : start + limit]
                    ]
                )
                await self.session.execute(
                    update(table)
                    .where(table.c.id == changed.c.id)
                    .values(
                        {key: cast(changed.c[key], table.c[key].type) for key in names}
                    )
                    .execution_options(**self.execution_options(tenant_id))
                )


__all__ = [
    "SessionRepository",
    "checked",
    "identifier",
    "entity_values",
    "PersistenceMappingError",
]
