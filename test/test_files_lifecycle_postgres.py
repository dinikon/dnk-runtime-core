"""Миграция, блокировки и ограничения lifecycle на одноразовом PostgreSQL."""

import asyncio
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
import os
import unittest
from uuid import uuid4

import sqlalchemy as sa
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool
from sqlalchemy.schema import CreateSchema, DropSchema

from src.modules.files.domain.error import FileNotFoundError
from src.modules.files.domain.stored_file.error import FileStateConflictError
from src.modules.files.domain.stored_file.aggregate import StoredFile
from src.modules.files.domain.stored_file.status import StoredFileStatus
from src.modules.files.domain.value_object.file_name import FileNameVO
from src.modules.files.domain.value_object.file_size import FileSizeVO
from src.modules.files.infrastructure.persistence.models.bucket import BucketModel
from src.modules.files.infrastructure.persistence.models.storage_provider import (
    StorageProviderModel,
)
from src.modules.files.infrastructure.persistence.models.stored_file import (
    StoredFileModel,
)
from src.modules.files.infrastructure.persistence.query_repository import (
    SqlAlchemyStorageQueryRepository,
)
from src.modules.files.infrastructure.stored_file.persistence.mapper import (
    StoredFileMapper,
)
from src.modules.files.infrastructure.stored_file.persistence.repository import (
    SqlAlchemyStoredFileRepository,
)
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_migrations import (
    TenantMigrator,
)

URL = os.environ.get("TEST_POSTGRES_URL")


@unittest.skipUnless(URL, "Disposable PostgreSQL required")
class StoredFileLifecyclePostgresTests(unittest.IsolatedAsyncioTestCase):
    """Проверяет настоящие транзакции без mock сессий и без рабочих данных."""

    async def asyncSetUp(self) -> None:
        """Создаёт отдельную tenant-схему и зарегистрированный готовый файл."""
        self.engine = create_async_engine(URL, poolclass=NullPool)
        self.schema = f"dnk_files_test_{uuid4().hex}"
        self.migrator = TenantMigrator()
        self.actor = EntityIdVO.from_value(uuid4())
        self.job = EntityIdVO.from_value(uuid4())
        self.tenant = uuid4()
        self.created = datetime(2026, 3, 1, 12, tzinfo=UTC)
        self.deleted = self.created + timedelta(days=1)
        provider_id, bucket_id = uuid4(), uuid4()
        self.file = StoredFile.create(
            file_id=EntityIdVO.from_value(uuid4()),
            bucket_id=EntityIdVO.from_value(bucket_id),
            name=FileNameVO("report.pdf"),
            content_type="application/pdf",
            size=FileSizeVO(10),
            created_at=self.created,
        )
        self.file.mark_uploaded(10)
        async with self.engine.begin() as connection:
            await connection.execute(CreateSchema(self.schema))
            await self.migrator.upgrade(connection, self.schema)
            await connection.execution_options(
                schema_translate_map={"tenant": self.schema}
            )
            await connection.execute(
                sa.insert(StorageProviderModel).values(
                    id=provider_id,
                    name="MinIO",
                    kind="minio",
                    is_system=True,
                    config_ref="system_minio",
                )
            )
            await connection.execute(
                sa.insert(BucketModel).values(
                    id=bucket_id,
                    provider_id=provider_id,
                    name=f"dnk-tenant-{uuid4().hex}",
                    status="ready",
                )
            )
            await connection.execute(
                sa.insert(StoredFileModel).values(
                    **StoredFileMapper.to_insert_values(self.file)
                )
            )

    async def asyncTearDown(self) -> None:
        """Удаляет только созданную этим тестом схему."""
        try:
            async with self.engine.begin() as connection:
                await connection.execute(
                    DropSchema(self.schema, cascade=True, if_exists=True)
                )
        finally:
            await self.engine.dispose()

    @asynccontextmanager
    async def session(self) -> AsyncIterator[AsyncSession]:
        """Передаёт repository внешнюю сессию с фиксированной tenant-схемой."""
        async with self.engine.connect() as connection:
            await connection.execution_options(
                schema_translate_map={"tenant": self.schema}
            )
            async with AsyncSession(connection, expire_on_commit=False) as session:
                yield session

    async def test_round_trip_rollback_and_ready_only_projections(self) -> None:
        """Корзина исключается из чтения и счётчиков, но защищается от orphan cleanup."""
        async with self.session() as session:
            repo = SqlAlchemyStoredFileRepository(session)
            query = SqlAlchemyStorageQueryRepository(session)
            aggregate = await repo.get_for_update(self.file.id)
            aggregate.move_to_trash(self.actor, self.deleted)
            await repo.save(aggregate)
            await session.rollback()
            self.assertEqual(
                (await repo.get(self.file.id)).status, StoredFileStatus.READY
            )
            aggregate = await repo.get_for_update(self.file.id)
            aggregate.move_to_trash(self.actor, self.deleted)
            await repo.save(aggregate)
            await session.commit()
        for status in (StoredFileStatus.TRASHED, StoredFileStatus.PURGING):
            async with self.session() as session:
                repo = SqlAlchemyStoredFileRepository(session)
                query = SqlAlchemyStorageQueryRepository(session)
                aggregate = await repo.get_for_update(self.file.id)
                if status == StoredFileStatus.PURGING:
                    aggregate.request_purge(self.deleted, self.job)
                    await repo.save(aggregate)
                self.assertEqual(await repo.get(self.file.id), aggregate)
                self.assertIsNone(
                    await query.content_location(self.tenant, self.file.id.uuid)
                )
                self.assertEqual((await query.buckets(None))[0].files_count, 0)
                self.assertEqual((await query.buckets(None))[0].size_bytes, 0)
                self.assertTrue(
                    await query.contains_key(
                        self.file.bucket_id.uuid, self.file.object_key
                    )
                )
                await session.commit()

    async def test_confirmed_removal_is_idempotent_and_rejects_stale_job(self) -> None:
        """Удаление требует подтверждения и совпадения сохранённого ID задания."""
        async with self.session() as session:
            repo = SqlAlchemyStoredFileRepository(session)
            aggregate = await repo.get_for_update(self.file.id)
            with self.assertRaises(FileStateConflictError):
                await repo.remove(aggregate)
            aggregate.move_to_trash(self.actor, self.deleted)
            aggregate.request_purge(self.deleted, self.job)
            await repo.save(aggregate)
            await session.commit()
        async with self.session() as session:
            repo = SqlAlchemyStoredFileRepository(session)
            stale = await repo.get_for_update(self.file.id)
            replacement = StoredFileMapper.to_domain(
                StoredFileModel(**StoredFileMapper.to_insert_values(stale))
            )
            new_job = EntityIdVO.from_value(uuid4())
            replacement.replace_purge_job(new_job)
            await repo.save(replacement)
            stale.mark_purged(self.job)
            with self.assertRaises(FileStateConflictError):
                await repo.remove(stale)
            replacement.mark_purged(new_job)
            await repo.remove(replacement)
            await session.rollback()
            self.assertEqual(
                (await repo.get(self.file.id)).status, StoredFileStatus.PURGING
            )
            aggregate = await repo.get_for_update(self.file.id)
            aggregate.mark_purged(self.job)
            await repo.remove(aggregate)
            await repo.remove(aggregate)
            await session.commit()
        async with self.session() as session:
            repo = SqlAlchemyStoredFileRepository(session)
            with self.assertRaises(FileNotFoundError):
                await repo.get_for_update(self.file.id)
            self.assertFalse(
                await SqlAlchemyStorageQueryRepository(session).contains_key(
                    self.file.bucket_id.uuid, self.file.object_key
                )
            )

    async def test_sql_constraints_reject_invalid_states_and_use_elapsed_hours(
        self,
    ) -> None:
        """SQL не допускает пустую корзину, неверные сроки или постоянный purged."""
        active = StoredFileMapper.to_insert_values(self.file)
        trash = active | {
            "status": "trashed",
            "deleted_at": self.deleted,
            "deleted_by": self.actor.uuid,
            "purge_after": self.deleted + timedelta(hours=720),
        }
        purge = trash | {
            "status": "purging",
            "purge_requested_at": self.deleted,
            "purge_job_id": self.job.uuid,
        }
        invalid = [
            active | {"deleted_by": self.actor.uuid},
            active | {"status": "trashed"},
            trash | {"deleted_by": None},
            trash | {"purge_after": None},
            trash | {"purge_job_id": self.job.uuid},
            trash | {"purge_after": self.deleted + timedelta(hours=719)},
            trash | {"deleted_at": self.created - timedelta(seconds=1)},
            purge | {"purge_requested_at": None},
            purge | {"purge_job_id": None},
            purge | {"purge_requested_at": self.deleted - timedelta(seconds=1)},
            purge | {"status": "purged"},
        ]
        async with self.session() as session:
            await session.execute(sa.text("SET LOCAL TIME ZONE 'Europe/Kyiv'"))
            for values in invalid:
                with self.subTest(values=values), self.assertRaises(IntegrityError):
                    async with session.begin_nested():
                        await session.execute(
                            sa.update(StoredFileModel)
                            .where(StoredFileModel.id == self.file.id.uuid)
                            .values(**values)
                        )
            await session.execute(
                sa.update(StoredFileModel)
                .where(StoredFileModel.id == self.file.id.uuid)
                .values(**trash)
            )
            aggregate = await SqlAlchemyStoredFileRepository(session).get(self.file.id)
            self.assertEqual(
                aggregate.purge_after - aggregate.deleted_at, timedelta(hours=720)
            )
            await session.commit()

    async def test_upgrade_preserves_old_rows_and_guarded_downgrade(self) -> None:
        """Upgrade сохраняет старые данные; downgrade требует пустую корзину."""
        async with self.engine.begin() as connection:
            await self.migrator.downgrade(connection, self.schema, "0020_files")
            uploading_id = uuid4()
            await connection.execute(
                sa.text(
                    f'INSERT INTO "{self.schema}".files_registry '
                    "(id,bucket_id,object_key,name,content_type,size_bytes,status,created_at) "
                    "VALUES (:id,:bucket,:key,:name,:mime,0,'uploading',:created)"
                ),
                {
                    "id": uploading_id,
                    "bucket": self.file.bucket_id.uuid,
                    "key": uploading_id.hex,
                    "name": "empty.txt",
                    "mime": "text/plain",
                    "created": self.created,
                },
            )
            before = (
                (
                    await connection.execute(
                        sa.text(
                            f'SELECT * FROM "{self.schema}".files_registry ORDER BY id'
                        )
                    )
                )
                .mappings()
                .all()
            )
            await self.migrator.upgrade(connection, self.schema)
            after = (
                (
                    await connection.execute(
                        sa.text(
                            f'SELECT * FROM "{self.schema}".files_registry ORDER BY id'
                        )
                    )
                )
                .mappings()
                .all()
            )
            for old, new in zip(before, after, strict=True):
                self.assertEqual(dict(old), {key: new[key] for key in old})
                self.assertTrue(
                    all(
                        new[key] is None
                        for key in (
                            "deleted_at",
                            "deleted_by",
                            "purge_after",
                            "purge_requested_at",
                            "purge_job_id",
                        )
                    )
                )
        async with self.session() as session:
            repo = SqlAlchemyStoredFileRepository(session)
            aggregate = await repo.get_for_update(self.file.id)
            aggregate.move_to_trash(self.actor, self.deleted)
            await repo.save(aggregate)
            await session.commit()
        for state in (StoredFileStatus.TRASHED, StoredFileStatus.PURGING):
            with (
                self.subTest(state=state),
                self.assertRaisesRegex(RuntimeError, "Cannot downgrade"),
            ):
                async with self.engine.begin() as connection:
                    await self.migrator.downgrade(connection, self.schema, "0020_files")
            async with self.session() as session:
                repo = SqlAlchemyStoredFileRepository(session)
                aggregate = await repo.get_for_update(self.file.id)
                if state == StoredFileStatus.TRASHED:
                    aggregate.request_purge(self.deleted, self.job)
                    await repo.save(aggregate)
                else:
                    aggregate.mark_purged(self.job)
                    await repo.remove(aggregate)
                await session.commit()
        async with self.engine.begin() as connection:
            self.assertEqual(
                await self.migrator.current(connection, self.schema),
                (self.migrator.head(),),
            )
            await self.migrator.downgrade(connection, self.schema, "0020_files")
            self.assertEqual(
                await self.migrator.current(connection, self.schema), ("0020_files",)
            )
            self.assertEqual(
                await connection.scalar(
                    sa.text(f'SELECT status FROM "{self.schema}".files_registry')
                ),
                "uploading",
            )
            await self.migrator.upgrade(connection, self.schema)

    async def wait_for_blocked_connection(self, pid: int) -> None:
        """Ждёт подтверждённого PostgreSQL ожидания lock без фиксированной задержки."""
        async with asyncio.timeout(5), self.engine.connect() as connection:
            while not await connection.scalar(
                sa.text(
                    "SELECT wait_event_type = 'Lock' FROM pg_stat_activity WHERE pid = :pid"
                ),
                {"pid": pid},
            ):
                await asyncio.sleep(0.01)

    async def test_waiting_purge_rechecks_committed_restore_and_refreshes_identity_map(
        self,
    ) -> None:
        """Ожидающая операция видит восстановление, даже если ORM ранее загрузил trash."""
        self.file.move_to_trash(self.actor, self.deleted)
        async with self.session() as seed:
            await SqlAlchemyStoredFileRepository(seed).save(self.file)
            await seed.commit()
        async with self.session() as restoring, self.session() as purging:
            old_row = await purging.get(StoredFileModel, self.file.id.uuid)
            pid = await purging.scalar(sa.text("SELECT pg_backend_pid()"))
            restore_repo = SqlAlchemyStoredFileRepository(restoring)
            aggregate = await restore_repo.get_for_update(self.file.id)
            aggregate.restore_from_trash(self.deleted + timedelta(days=29))
            await restore_repo.save(aggregate)
            waiter = asyncio.create_task(
                SqlAlchemyStoredFileRepository(purging).get_for_update(self.file.id)
            )
            try:
                await self.wait_for_blocked_connection(pid)
                self.assertFalse(waiter.done())
                await restoring.commit()
                refreshed = await asyncio.wait_for(waiter, 5)
                self.assertEqual(old_row.status, "ready")
                with self.assertRaises(FileStateConflictError):
                    refreshed.request_expired_purge(
                        self.deleted + timedelta(days=30), self.job
                    )
            finally:
                if not waiter.done():
                    waiter.cancel()
                    await asyncio.gather(waiter, return_exceptions=True)

    async def test_waiting_restore_rejects_committed_purge(self) -> None:
        """Если purge получил lock первым, восстановление не возвращает файл в ready."""
        self.file.move_to_trash(self.actor, self.deleted)
        async with self.session() as seed:
            await SqlAlchemyStoredFileRepository(seed).save(self.file)
            await seed.commit()
        async with self.session() as purging, self.session() as restoring:
            pid = await restoring.scalar(sa.text("SELECT pg_backend_pid()"))
            repo = SqlAlchemyStoredFileRepository(purging)
            aggregate = await repo.get_for_update(self.file.id)
            aggregate.request_expired_purge(self.deleted + timedelta(days=30), self.job)
            await repo.save(aggregate)
            waiter = asyncio.create_task(
                SqlAlchemyStoredFileRepository(restoring).get_for_update(self.file.id)
            )
            try:
                await self.wait_for_blocked_connection(pid)
                await purging.commit()
                refreshed = await asyncio.wait_for(waiter, 5)
                self.assertEqual(refreshed.status, StoredFileStatus.PURGING)
                with self.assertRaises(FileStateConflictError):
                    refreshed.restore_from_trash(self.deleted + timedelta(days=30))
            finally:
                if not waiter.done():
                    waiter.cancel()
                    await asyncio.gather(waiter, return_exceptions=True)

    async def test_downgrade_waits_for_transition_then_rechecks_guard(self) -> None:
        """Откат не теряет trash, закоммиченный во время ожидания DDL lock."""
        async with self.session() as deleting:
            repo = SqlAlchemyStoredFileRepository(deleting)
            aggregate = await repo.get_for_update(self.file.id)
            aggregate.move_to_trash(self.actor, self.deleted)
            await repo.save(aggregate)
            with self.assertRaisesRegex(RuntimeError, "Cannot downgrade"):
                async with self.engine.begin() as connection:
                    pid = await connection.scalar(sa.text("SELECT pg_backend_pid()"))
                    waiter = asyncio.create_task(
                        self.migrator.downgrade(connection, self.schema, "0020_files")
                    )
                    try:
                        await self.wait_for_blocked_connection(pid)
                        self.assertFalse(waiter.done())
                        await deleting.commit()
                        await asyncio.wait_for(waiter, 5)
                    finally:
                        if not waiter.done():
                            waiter.cancel()
                            await asyncio.gather(waiter, return_exceptions=True)
        async with self.session() as session:
            self.assertEqual(
                (
                    await SqlAlchemyStoredFileRepository(session).get(self.file.id)
                ).status,
                StoredFileStatus.TRASHED,
            )
