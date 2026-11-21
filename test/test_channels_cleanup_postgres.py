"""Очистка заполненных tenant-таблиц и общей очереди без потери подключений."""

from datetime import UTC, datetime
import importlib.util
from pathlib import Path
from unittest import TestLoader, TestSuite
from uuid import uuid4

from alembic import command
from alembic.migration import MigrationContext
from alembic.operations import Operations
import sqlalchemy as sa
from sqlalchemy.schema import CreateSchema

from src.modules.shared.infrastructure.jobs.scheduled_job_model import ScheduledJobModel
from src.modules.shared.infrastructure.events.integration_outbox_event_model import (
    IntegrationOutboxEventModel,
)
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_migrations import (
    TenantMigrator,
)
from src.modules.shared.infrastructure.persistence.alembic_lock import (
    serialized_alembic,
)
from test import test_channels_postgres as support

TABLES = (
    "channel_sync_runs",
    "channel_external_publications",
    "channel_catalog_binding_groups",
    "channel_catalog_binding_items",
    "channel_stock_sync_states",
    "channel_product_representations",
    "channel_content_media",
    "channel_content_feeds",
    "channel_content_deliveries",
)


class ChannelsCleanupPostgresTests(support.ChannelsPostgresTests):
    """Проверяет новую ревизию на настоящих заполненных исторических таблицах."""

    async def test_populated_upgrade_preserves_connections_and_other_tenant(
        self,
    ) -> None:
        """DROP работает с FK; credentials, identity, аудит и соседние таблицы сохранены."""
        created = await self.create()
        channels = await self.rows(support.ChannelModel)
        connections = await self.rows(support.ConnectionModel)
        schema = "channels_legacy_" + uuid4().hex[:16]
        self.schemas.append(schema)
        now = datetime.now(UTC)
        async with self.engine.begin() as connection:
            await connection.execute(CreateSchema(schema))
            config = TenantMigrator().config(schema)

            def previous_revision(sync: sa.Connection) -> None:
                """Создаёт состояние перед очисткой штатным Alembic environment."""
                config.attributes["connection"] = sync
                command.upgrade(config, "0015_channels_feed_import")

            async with serialized_alembic():
                await connection.run_sync(previous_revision)
            metadata = sa.MetaData()
            await connection.run_sync(lambda c: metadata.reflect(c, schema=schema))
            await connection.execute(
                metadata.tables[f"{schema}.channels"].insert(),
                [dict(row) for row in channels],
            )
            legacy_connection = dict(connections[0])
            legacy_connection["identity_namespace"] = "prom.root_group"
            legacy_connection["identity_key"] = "7"
            legacy_connection["verification"] = {
                **legacy_connection["verification"],
                "status": "verified",
                "checked_at": now.isoformat(),
                "error_code": None,
            }
            legacy_connection["settings"] = {
                "currency": "UAH",
                "locales": ["uk", "ru"],
                "stock_sync": {
                    "allow_export": True,
                    "revision": 2,
                    "changed_at": now.isoformat(),
                },
            }
            await connection.execute(
                metadata.tables[f"{schema}.channel_connections"].insert(),
                legacy_connection,
            )
            identifiers = {name: uuid4() for name in TABLES}
            known = {
                "connection_id": legacy_connection["id"],
                "publication_id": identifiers["channel_external_publications"],
                "last_sync_run_id": identifiers["channel_sync_runs"],
                "group_id": identifiers["channel_catalog_binding_groups"],
                "binding_group_id": identifiers["channel_catalog_binding_groups"],
                "representation_id": identifiers["channel_product_representations"],
            }
            for name in TABLES:
                table = metadata.tables[f"{schema}.{name}"]
                values = {}
                for column in table.columns:
                    if column.name == "id":
                        values[column.name] = identifiers[name]
                    elif column.name in known:
                        values[column.name] = known[column.name]
                    elif column.nullable:
                        values[column.name] = None
                    elif column.server_default is not None:
                        continue
                    elif isinstance(column.type, sa.Uuid):
                        values[column.name] = uuid4()
                    elif isinstance(column.type, sa.DateTime):
                        values[column.name] = now
                    elif isinstance(column.type, sa.Boolean):
                        values[column.name] = False
                    elif isinstance(column.type, sa.Integer):
                        values[column.name] = 1
                    elif isinstance(column.type, sa.JSON):
                        values[column.name] = {}
                    elif isinstance(column.type, sa.LargeBinary):
                        values[column.name] = b"fixture"
                    else:
                        values[column.name] = "fixture"
                await connection.execute(table.insert(), values)
            keep = sa.Table(
                "cleanup_neighbor",
                sa.MetaData(),
                sa.Column("id", sa.UUID(), primary_key=True),
                sa.Column("value", sa.Text()),
                schema=schema,
            )
            await connection.run_sync(lambda c: keep.create(c))
            marker = uuid4()
            await connection.execute(keep.insert().values(id=marker, value="keep"))
        async with self.engine.begin() as connection:
            await TenantMigrator().upgrade(connection, schema)
            names = set(
                await connection.run_sync(
                    lambda c: sa.inspect(c).get_table_names(schema=schema)
                )
            )
            self.assertFalse(names.intersection(TABLES))
            self.assertTrue(
                {
                    "channels",
                    "channel_connections",
                    "catalog_item",
                    "files_registry",
                    "cleanup_neighbor",
                }
                <= names
            )
            self.assertEqual(
                await connection.scalar(
                    sa.select(keep.c.value).where(keep.c.id == marker)
                ),
                "keep",
            )
            preserved = (
                (
                    await connection.execute(
                        sa.select(metadata.tables[f"{schema}.channel_connections"])
                    )
                )
                .mappings()
                .one()
            )
            self.assertEqual(dict(preserved), legacy_connection | {"settings": {}})
            preserved_channels = (
                (
                    await connection.execute(
                        sa.select(metadata.tables[f"{schema}.channels"])
                    )
                )
                .mappings()
                .all()
            )
            self.assertEqual(
                [dict(row) for row in preserved_channels],
                [dict(row) for row in channels],
            )
        self.assertEqual(await self.rows(support.ChannelModel), channels)
        self.assertEqual(await self.rows(support.ConnectionModel), connections)
        async with self.engine.begin() as connection:
            await TenantMigrator().upgrade(connection, schema)
        detail = await self.detail(created["id"])
        self.assertEqual(
            detail["config"]["settings"],
            {"currency": "UAH", "locales": ["ru", "uk"]},
        )

    async def test_global_cleanup_preserves_verification_other_jobs_and_outbox(
        self,
    ) -> None:
        """Удаляются только точные типы; одинаковый префикс не расширяет область."""
        removed = (
            "channels.sync_publications",
            "channels.sync_stock",
            "channels.deliver_content",
            "channels.apply_content_feed",
            "catalog.stock_changed",
        )
        retained = (
            "channels.verify_connection",
            "files.purge",
            "catalog.import.run",
            "channels.future_task",
        )
        path = (
            Path(__file__).resolve().parents[1]
            / "migrations/global/versions/0002_channels_jobs_cleanup.py"
        )
        spec = importlib.util.spec_from_file_location(
            "channels_jobs_cleanup_test", path
        )
        migration = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(migration)
        now = datetime.now(UTC)
        async with self.engine.begin() as connection:
            existing_jobs = set(
                (
                    await connection.execute(
                        sa.select(
                            ScheduledJobModel.tenant_id, ScheduledJobModel.job_type
                        )
                    )
                ).all()
            )
            await connection.run_sync(
                lambda c: IntegrationOutboxEventModel.__table__.create(
                    c, checkfirst=True
                )
            )
            event_id = uuid4()
            await connection.execute(
                sa.insert(IntegrationOutboxEventModel).values(
                    id=event_id,
                    tenant_id=self.tenant,
                    event_type="catalog.stock_changed",
                    event_version=1,
                    aggregate_type="catalog_item",
                    aggregate_id=uuid4(),
                    payload={"position_ids": []},
                    occurred_at=now,
                    status="pending",
                    publish_attempts=0,
                )
            )
            event_before = (
                (
                    await connection.execute(
                        sa.select(IntegrationOutboxEventModel.__table__).where(
                            IntegrationOutboxEventModel.id == event_id
                        )
                    )
                )
                .mappings()
                .one()
            )
            for tenant in (self.tenant, self.other):
                for job_type in (*removed, *retained):
                    await connection.execute(
                        sa.insert(ScheduledJobModel).values(
                            id=uuid4(),
                            tenant_id=tenant,
                            job_type=job_type,
                            payload={},
                            run_at=now,
                            status="scheduled",
                            attempts=0,
                        )
                    )

            def upgrade(sync: sa.Connection) -> None:
                """Исполняет только новую global-ревизию на общей очереди fixtures."""
                with Operations.context(MigrationContext.configure(sync)):
                    migration.upgrade()

            await connection.run_sync(upgrade)
            rows = (
                await connection.execute(
                    sa.select(ScheduledJobModel.tenant_id, ScheduledJobModel.job_type)
                )
            ).all()
            self.assertEqual(
                set(rows),
                {
                    (tenant, kind)
                    for tenant in (self.tenant, self.other)
                    for kind in retained
                }
                | {
                    (tenant, kind)
                    for tenant, kind in existing_jobs
                    if kind not in removed
                },
            )
            event_after = (
                (
                    await connection.execute(
                        sa.select(IntegrationOutboxEventModel.__table__).where(
                            IntegrationOutboxEventModel.id == event_id
                        )
                    )
                )
                .mappings()
                .one()
            )
            self.assertEqual(dict(event_after), dict(event_before))
            await connection.execute(
                sa.delete(IntegrationOutboxEventModel).where(
                    IntegrationOutboxEventModel.id == event_id
                )
            )
        with self.assertRaisesRegex(RuntimeError, "необратима"):
            migration.downgrade()


def load_tests(loader: TestLoader, tests: TestSuite, pattern: str | None) -> TestSuite:
    """Не дублирует сценарии родительского набора HTTP."""
    return TestSuite(
        ChannelsCleanupPostgresTests(name)
        for name in ChannelsCleanupPostgresTests.__dict__
        if name.startswith("test_")
    )
