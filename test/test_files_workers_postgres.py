"""Файловые worker на одноразовых PostgreSQL/MinIO, с реальными locks и версиями."""

import asyncio
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from io import BytesIO
import os
from pathlib import Path
import threading
import unittest
from unittest.mock import AsyncMock, patch
from uuid import UUID, uuid4, uuid5

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import async_sessionmaker
from minio.versioningconfig import VersioningConfig
from minio.commonconfig import ENABLED

from src.config import dnk_config
from src.modules.files.application.stored_file.command.cleanup_expired_trash.command import (
    CleanupExpiredTrashCommand,
)
from src.modules.files.application.stored_file.command.purge_file.command import (
    PurgeFileCommand,
)
from src.modules.files.application.port.storage import (
    StorageUnavailableError,
    StorageOwnershipError,
)
from src.modules.files.domain.stored_file.aggregate import StoredFile
from src.modules.files.domain.value_object.file_name import FileNameVO
from src.modules.files.domain.value_object.file_size import FileSizeVO
from src.modules.files.infrastructure.assembly import build_files_handlers
from src.modules.files.infrastructure.persistence.models.stored_file import (
    StoredFileModel,
)
from src.modules.files.infrastructure.stored_file.persistence.mapper import (
    StoredFileMapper,
)
from src.modules.files.infrastructure.stored_file.jobs.purge_queue import (
    ScheduledFilePurgeQueue,
)
from src.modules.files.presentation.jobs.cleanup import ensure_cleanup_jobs
from src.modules.files.presentation.jobs.purge_file import FilesPurgeJobHandler
from src.modules.files.presentation.jobs.trash_cleanup import (
    FilesTrashCleanupJobHandler,
    ensure_trash_cleanup_jobs,
)
from src.modules.shared.application.jobs.schedule_scheduled_job_use_case import (
    ScheduleScheduledJobUseCase,
)
from src.modules.shared.application.jobs.scheduled_job_deferred import (
    ScheduledJobDeferred,
)
from src.modules.shared.application.jobs.in_memory_scheduled_job_dispatcher import (
    InMemoryScheduledJobDispatcher,
)
from src.modules.shared.domain.jobs.scheduled_job import ScheduledJob
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.shared.infrastructure.jobs.scheduled_job_model import ScheduledJobModel
from src.modules.shared.infrastructure.jobs.sqlalchemy_scheduled_job_repository import (
    SqlAlchemyScheduledJobRepository,
)
from src.modules.shared.infrastructure.jobs.worker import ScheduledJobWorker
from src.modules.shared.infrastructure.persistence.unit_of_work.sqlalchemy import (
    UnitOfWork,
)
from src.modules.shared.infrastructure.uuid.uuid7_generator import UUID7Generator
from src.modules.tenancy.infrastructure.persistence.tenant import TenantModel
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_gate import TenantGate
from src.modules.tenancy.application.tenant.tenant_admission import TenantUnavailable
from test import test_files_mutations_postgres as support


@unittest.skipUnless(
    os.environ.get("TEST_POSTGRES_URL") and os.environ.get("TEST_MINIO_ENDPOINT"),
    "Disposable services required",
)
class FilesWorkerPostgresTests(unittest.IsolatedAsyncioTestCase):
    """Проверяет повторное удаление, recovery и durable continuation без рабочих данных."""

    context = support.FilesMutationPostgresTests.context
    session = support.FilesMutationPostgresTests.session
    add_file = support.FilesMutationPostgresTests.add_file
    get = support.FilesMutationPostgresTests.get

    async def asyncSetUp(self) -> None:
        """Готовит настоящие tenant names и admission записи поверх файловой fixture."""
        await support.FilesMutationPostgresTests.asyncSetUp(self)
        async with self.engine.begin() as connection:
            for tenant in self.tenants:
                old = self.schemas[tenant]
                new = f"{dnk_config.SCHEMA_PREFIX}{tenant.hex}"
                await connection.execute(
                    sa.text(f'ALTER SCHEMA "{old}" RENAME TO "{new}"')
                )
                self.schemas[tenant] = new
                await connection.execute(
                    sa.insert(TenantModel).values(
                        id=tenant,
                        name="Files worker test",
                        external_id=str(tenant),
                        status="active",
                    )
                )
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        self.cutoff = datetime.now(UTC) - timedelta(seconds=2)
        self.now = self.cutoff - timedelta(days=31)
        self.purge = FilesPurgeJobHandler(self.sessions)
        self.cleanup = FilesTrashCleanupJobHandler(self.sessions)

    async def asyncTearDown(self) -> None:
        """Удаляет только созданные этой fixture записи tenant и storage."""
        async with self.engine.begin() as connection:
            await connection.execute(
                sa.delete(TenantModel).where(TenantModel.id.in_(self.tenants))
            )
        await support.FilesMutationPostgresTests.asyncTearDown(self)

    def queue(self, session) -> ScheduledFilePurgeQueue:
        """Собирает очередь и репозиторий jobs на одной сессии теста."""
        jobs = SqlAlchemyScheduledJobRepository(session)
        return ScheduledFilePurgeQueue(
            ScheduleScheduledJobUseCase(
                repository=jobs, clock=self.clock, uuid_generator=UUID7Generator()
            ),
            jobs,
        )

    async def claim(self, job_id: UUID) -> ScheduledJob:
        """Эмулирует committed claim одного конкретного задания с настоящей lease."""
        async with self.sessions() as session:
            await session.execute(
                sa.update(ScheduledJobModel)
                .where(ScheduledJobModel.id == job_id)
                .values(
                    status="running",
                    lock_token=str(uuid4()),
                    locked_until=datetime.now(UTC) + timedelta(minutes=5),
                    attempts=ScheduledJobModel.attempts + 1,
                )
            )
            model = await session.get(ScheduledJobModel, job_id)
            job = ScheduledJob(
                id=model.id,
                tenant_id=model.tenant_id,
                job_type=model.job_type,
                payload=dict(model.payload),
                run_at=model.run_at,
                status=model.status,
                attempts=model.attempts,
                locked_until=model.locked_until,
                lock_token=model.lock_token,
                created_at=model.created_at,
                updated_at=model.updated_at,
            )
            await session.commit()
            return job

    async def scan_job(self, *, cutoff: datetime | None = None) -> ScheduledJob:
        """Ставит и забирает первый проход корзины с фиксированным cutoff."""
        job_id = uuid4()
        async with self.sessions() as session:
            await self.queue(session).schedule_cleanup(
                self.tenants[0], job_id, cutoff or self.cutoff
            )
            await session.commit()
        return await self.claim(job_id)

    async def purge_job(self, file: StoredFile) -> ScheduledJob:
        """Ставит job текущего purging файла в отдельном committed UoW."""
        async with self.sessions() as session:
            await self.queue(session).schedule(
                self.tenants[0], file.id.uuid, file.purge_job_id.uuid, self.cutoff
            )
            await session.commit()
        return await self.claim(file.purge_job_id.uuid)

    async def record(self, file: StoredFile) -> StoredFileModel | None:
        """Читает сохранённую регистрацию независимо от worker-транзакции."""
        async with self.session() as session:
            return await session.get(StoredFileModel, file.id.uuid)

    async def job_models(self, *, kind: str | None = None) -> list[ScheduledJobModel]:
        """Возвращает только jobs текущего tenant."""
        async with self.sessions() as session:
            statement = sa.select(ScheduledJobModel).where(
                ScheduledJobModel.tenant_id == self.tenants[0]
            )
            if kind:
                statement = statement.where(ScheduledJobModel.job_type == kind)
            return list(await session.scalars(statement))

    async def put(self, file: StoredFile, content: bytes = b"old") -> None:
        """Загружает owned-объект теста, включая повторную версию одного ключа."""
        await self.adapter.put(
            self.locations[0],
            file.object_key,
            BytesIO(content),
            len(content),
            "application/pdf",
        )

    async def test_versioned_purge_removes_all_versions_markers_and_only_one_key(
        self,
    ) -> None:
        """Purge освобождает скрытые версии и markers, сохраняя соседний ключ и бакет."""
        file = await self.add_file("versioned.pdf", status="purging")
        other = await self.add_file("neighbor.pdf")
        await self.adapter.call(
            lambda: self.adapter._client.set_bucket_versioning(
                self.locations[0].bucket_name, VersioningConfig(ENABLED)
            )
        )
        await self.put(file)
        await self.put(file, b"new")
        await self.put(other)
        # Prefix совпадает, но это другой ключ: удаление обязано проверять точное имя.
        await self.adapter.call(
            lambda: self.adapter._client.put_object(
                self.locations[0].bucket_name,
                file.object_key + "suffix",
                BytesIO(b"x"),
                1,
            )
        )
        await self.adapter.remove(self.locations[0], file.object_key)
        job = await self.purge_job(file)
        await asyncio.gather(self.purge.handle(job), self.purge.handle(job))
        self.assertIsNone(await self.record(file))
        self.assertTrue(
            await self.adapter.exists_owned(self.locations[0], other.object_key)
        )
        versions = await self.adapter.call(
            lambda: list(
                self.adapter._client.list_objects(
                    self.locations[0].bucket_name,
                    prefix=file.object_key,
                    include_version=True,
                    recursive=True,
                )
            )
        )
        self.assertEqual(
            [obj.object_name for obj in versions], [file.object_key + "suffix"]
        )
        await self.purge.handle(job)

    async def test_version_listing_over_1000_versions_does_not_skip_deleted_page_marker(
        self,
    ) -> None:
        """Удаление во время paged listing не пропускает следующую страницу версий."""
        file = await self.add_file("many-versions.pdf", status="purging")
        location = self.locations[0]
        await self.adapter.call(
            lambda: self.adapter._client.set_bucket_versioning(
                location.bucket_name, VersioningConfig(ENABLED)
            )
        )

        def prepare_versions() -> None:
            for index in range(1005):
                self.adapter._client.put_object(
                    location.bucket_name,
                    file.object_key,
                    BytesIO(),
                    0,
                    metadata={
                        "dnk-tenant": str(location.tenant_id),
                        "dnk-bucket": str(location.bucket_id),
                        "dnk-file": file.object_key,
                    },
                )

        await self.adapter.call(prepare_versions)
        await self.purge.handle(await self.purge_job(file))
        self.assertIsNone(await self.record(file))
        self.assertFalse(
            await self.adapter.call(
                lambda: any(
                    self.adapter._client.list_objects(
                        location.bucket_name,
                        prefix=file.object_key,
                        include_version=True,
                    )
                )
            )
        )

    async def test_storage_outage_and_foreign_historical_version_preserve_registry(
        self,
    ) -> None:
        """Ошибки storage не удаляют реестр, а старые unowned-версии не стираются."""
        file = await self.add_file("ownership.pdf", status="purging")
        job = await self.purge_job(file)
        with patch.object(
            self.adapter,
            "remove_owned_versions",
            AsyncMock(side_effect=StorageUnavailableError()),
        ):
            with self.assertRaises(StorageUnavailableError):
                await self.purge.handle(job)
        self.assertEqual((await self.record(file)).status, "purging")
        location = self.locations[0]
        try:
            await self.adapter.call(
                lambda: self.adapter._client.set_bucket_tags(
                    location.bucket_name,
                    self.adapter._tags(
                        {
                            "dnk_tenant": str(uuid4()),
                            "dnk_bucket": str(location.bucket_id),
                        }
                    ),
                )
            )
            with self.assertRaises(StorageOwnershipError):
                await self.purge.handle(job)
            self.assertEqual((await self.record(file)).status, "purging")
        finally:
            await self.adapter.call(
                lambda: self.adapter._client.set_bucket_tags(
                    location.bucket_name,
                    self.adapter._tags(
                        {
                            "dnk_tenant": str(location.tenant_id),
                            "dnk_bucket": str(location.bucket_id),
                        }
                    ),
                )
            )
        await self.adapter.call(
            lambda: self.adapter._client.set_bucket_versioning(
                self.locations[0].bucket_name, VersioningConfig(ENABLED)
            )
        )
        foreign = await self.adapter.call(
            lambda: self.adapter._client.put_object(
                self.locations[0].bucket_name, file.object_key, BytesIO(b"foreign"), 7
            )
        )
        await self.put(file)
        await self.adapter.remove(self.locations[0], file.object_key)
        with self.assertRaises(StorageOwnershipError):
            await self.purge.handle(job)
        self.assertIsNotNone(await self.record(file))
        self.assertEqual(
            (
                await self.adapter.call(
                    lambda: self.adapter._client.stat_object(
                        self.locations[0].bucket_name,
                        file.object_key,
                        version_id=foreign.version_id,
                    )
                )
            ).size,
            7,
        )

    async def test_already_absent_bucket_confirms_purge_and_malformed_envelope_is_rejected(
        self,
    ) -> None:
        """Отсутствующий бакет допускает повтор; подмена tenant/job ID не вызывает SDK."""
        file = await self.add_file("absent.pdf", status="purging")
        job = await self.purge_job(file)
        for field in ("tenant_id", "job_id"):
            with self.assertRaises(ValueError):
                await self.purge.handle(
                    replace(job, payload={**job.payload, field: str(uuid4())})
                )
        self.assertIsNotNone(await self.record(file))
        await self.adapter.purge(self.locations[0])
        await self.purge.handle(job)
        self.assertIsNone(await self.record(file))

    async def test_physical_delete_then_failed_commit_retries_absent_object(
        self,
    ) -> None:
        """После сбоя commit реестр остаётся purging; повтор безопасно подтверждает отсутствие."""
        file = await self.add_file("crash.pdf", status="purging")
        await self.put(file)
        job = await self.purge_job(file)
        with patch.object(
            UnitOfWork,
            "commit",
            AsyncMock(side_effect=RuntimeError("simulated crash before SQL commit")),
        ):
            with self.assertRaises(RuntimeError):
                await self.purge.handle(job)
        self.assertEqual((await self.record(file)).status, "purging")
        self.assertFalse(
            await self.adapter.exists_owned(self.locations[0], file.object_key)
        )
        await self.purge.handle(job)
        self.assertIsNone(await self.record(file))

    async def test_stale_file_job_and_lost_lease_cannot_commit(self) -> None:
        """Старая job не вызывает SDK; смена lease во время SDK откатывает SQL."""
        file = await self.add_file("stale.pdf", status="purging")
        await self.put(file)
        stale_id = uuid4()
        async with self.sessions() as session:
            await self.queue(session).schedule(
                self.tenants[0], file.id.uuid, stale_id, self.cutoff
            )
            await session.commit()
        stale = await self.claim(stale_id)
        with patch.object(
            self.adapter,
            "remove_owned_versions",
            wraps=self.adapter.remove_owned_versions,
        ) as remove:
            await self.purge.handle(stale)
            remove.assert_not_called()
        job = await self.purge_job(file)
        actual = self.adapter.remove_owned_versions

        async def change_lease(location, key) -> None:
            await actual(location, key)
            async with self.sessions() as session:
                await session.execute(
                    sa.update(ScheduledJobModel)
                    .where(ScheduledJobModel.id == job.id)
                    .values(lock_token="new-lease")
                )
                await session.commit()

        with patch.object(self.adapter, "remove_owned_versions", change_lease):
            with self.assertRaises(ScheduledJobDeferred):
                await self.purge.handle(job)
        self.assertEqual((await self.record(file)).status, "purging")
        with patch.object(self.adapter, "remove_owned_versions", AsyncMock()) as remove:
            await self.purge.handle(job)
            remove.assert_not_called()
        await self.purge.handle(await self.claim(job.id))
        self.assertIsNone(await self.record(file))

    async def test_cancellation_waits_for_sdk_before_releasing_gate_and_file_lock(
        self,
    ) -> None:
        """Отмена не отпускает admission и row lock, пока синхронное удаление ещё работает."""
        file = await self.add_file("cancel.pdf", status="purging")
        await self.put(file)
        job = await self.purge_job(file)
        entered, finish = threading.Event(), threading.Event()
        actual = self.adapter._client.remove_object

        def blocking_delete(*args, **kwargs):
            entered.set()
            finish.wait(5)
            return actual(*args, **kwargs)

        with patch.object(self.adapter._client, "remove_object", blocking_delete):
            task = asyncio.create_task(self.purge.handle(job))
            try:
                self.assertTrue(await asyncio.to_thread(entered.wait, 3))
                task.cancel()
                await asyncio.sleep(0.05)
                self.assertFalse(task.done())
                with self.assertRaises(TenantUnavailable):
                    async with TenantGate(self.sessions).hold(
                        self.tenants[0], exclusive=True
                    ):
                        pass
                async with self.session() as session:
                    await session.execute(sa.text("SET LOCAL lock_timeout = '100ms'"))
                    with self.assertRaises(sa.exc.DBAPIError):
                        await session.execute(
                            sa.select(StoredFileModel)
                            .where(StoredFileModel.id == file.id.uuid)
                            .with_for_update()
                        )
            finally:
                finish.set()
                with self.assertRaises(asyncio.CancelledError):
                    await task
        self.assertEqual((await self.record(file)).status, "purging")
        await self.purge.handle(job)
        self.assertIsNone(await self.record(file))

    async def test_30_day_boundary_and_missing_canceled_failed_jobs_recover_once(
        self,
    ) -> None:
        """720 часов проверяются точно; terminal/missing меняются, running/scheduled сохраняются."""
        exact = await self.add_file(
            "exact.pdf", status="trashed", deleted=self.cutoff - timedelta(days=30)
        )
        young = await self.add_file(
            "young.pdf",
            status="trashed",
            deleted=self.cutoff - timedelta(days=30) + timedelta(microseconds=1),
        )
        stopped, active = [], []
        for status in (None, "done", "failed", "canceled", "scheduled", "running"):
            file = await self.add_file(f"{status}.pdf", status="purging")
            if status is not None:
                async with self.sessions() as session:
                    await self.queue(session).schedule(
                        self.tenants[0],
                        file.id.uuid,
                        file.purge_job_id.uuid,
                        self.cutoff,
                    )
                    await session.execute(
                        sa.update(ScheduledJobModel)
                        .where(ScheduledJobModel.id == file.purge_job_id.uuid)
                        .values(status=status)
                    )
                    await session.commit()
            (active if status in {"scheduled", "running"} else stopped).append(file)
        async with self.session() as session:
            backlog = await build_files_handlers(
                session
            ).cleanup_trash._queries.cleanup_backlog(self.cutoff)
            self.assertEqual(
                (backlog.expired_count, backlog.expired_size_bytes), (1, 10)
            )
            self.assertEqual(
                (backlog.pending_count, backlog.pending_size_bytes), (6, 60)
            )
            self.assertEqual(
                backlog.oldest_purge_after, self.cutoff - timedelta(days=1)
            )
        job = await self.scan_job()
        await self.cleanup.handle(job)
        self.assertEqual((await self.record(exact)).status, "purging")
        self.assertEqual((await self.record(young)).status, "trashed")
        for file in stopped:
            row = await self.record(file)
            self.assertNotEqual(row.purge_job_id, file.purge_job_id.uuid)
            self.assertEqual(row.deleted_at, file.deleted_at)
            self.assertEqual(row.purge_requested_at, file.purge_requested_at)
        for file in active:
            self.assertEqual(
                (await self.record(file)).purge_job_id, file.purge_job_id.uuid
            )
        before = len(await self.job_models())
        await self.cleanup.handle(job)
        self.assertEqual(len(await self.job_models()), before)

    async def test_more_than_100_candidates_continuation_survives_repeat_and_restart(
        self,
    ) -> None:
        """Первые 100 running не закрывают доступ к следующим истёкшим файлам; cursor durable."""
        files = []
        async with self.session() as session:
            for number in range(1, 112):
                file = StoredFile.create(
                    file_id=EntityIdVO.from_value(UUID(int=number)),
                    bucket_id=EntityIdVO.from_value(self.buckets[0]),
                    name=FileNameVO(f"{number}.pdf"),
                    content_type="application/pdf",
                    size=FileSizeVO(1),
                    created_at=self.now,
                )
                file.mark_uploaded(1)
                file.move_to_trash(EntityIdVO.from_value(uuid4()), self.now)
                if number <= 100:
                    file.request_purge(self.now, EntityIdVO.from_value(uuid4()))
                    await self.queue(session).schedule(
                        self.tenants[0],
                        file.id.uuid,
                        file.purge_job_id.uuid,
                        self.cutoff,
                    )
                    await session.execute(
                        sa.update(ScheduledJobModel)
                        .where(ScheduledJobModel.id == file.purge_job_id.uuid)
                        .values(status="running")
                    )
                await session.execute(
                    sa.insert(StoredFileModel).values(
                        **StoredFileMapper.to_insert_values(file)
                    )
                )
                files.append(file)
            await session.commit()
        job = await self.scan_job()
        await self.cleanup.handle(job)
        continuation_id = uuid5(job.id, f"after:{UUID(int=100)}")
        scan_jobs = await self.job_models(kind="files.trash.cleanup")
        self.assertEqual({item.id for item in scan_jobs}, {job.id, continuation_id})
        child = next(item for item in scan_jobs if item.id == continuation_id)
        self.assertEqual(child.payload["cutoff"], self.cutoff.isoformat())
        await self.cleanup.handle(job)
        self.assertEqual(len(await self.job_models(kind="files.trash.cleanup")), 2)
        # Новый runtime читает сохранённый cursor после условного restart.
        await FilesTrashCleanupJobHandler(self.sessions).handle(
            await self.claim(continuation_id)
        )
        self.assertEqual(len(await self.job_models(kind="files.purge")), 111)
        for file in files[100:]:
            self.assertEqual((await self.record(file)).status, "purging")

    async def test_cleanup_rolls_back_batch_and_continuation_on_failure(self) -> None:
        """Ошибка записи continuation откатывает вместе статус и все дочерние jobs."""
        file = await self.add_file("atomic.pdf", status="trashed")
        job = await self.scan_job()
        job = replace(job, payload={**job.payload, "batch_size": 1})
        original = ScheduledFilePurgeQueue.schedule_cleanup

        async def fail_after_insert(queue, *args, **kwargs) -> None:
            await original(queue, *args, **kwargs)
            raise RuntimeError("continuation write failed")

        with patch.object(
            ScheduledFilePurgeQueue, "schedule_cleanup", fail_after_insert
        ):
            with self.assertRaises(RuntimeError):
                await self.cleanup.handle(job)
        self.assertEqual((await self.record(file)).status, "trashed")
        self.assertEqual([item.id for item in await self.job_models()], [job.id])
        with patch.object(
            SqlAlchemyScheduledJobRepository,
            "owns_current_lease",
            AsyncMock(side_effect=[True, False]),
        ):
            with self.assertRaises(ScheduledJobDeferred):
                await self.cleanup.handle(job)
        self.assertEqual((await self.record(file)).status, "trashed")
        self.assertEqual([item.id for item in await self.job_models()], [job.id])
        await self.cleanup.handle(job)
        self.assertEqual((await self.record(file)).status, "purging")
        self.assertEqual(len(await self.job_models()), 3)

    async def test_registrar_old_tenants_freeze_dedup_and_exclusive_admission(
        self,
    ) -> None:
        """Старые tenant обслуживаются без onboarding; запрет gate и отсутствие схемы соблюдаются."""
        unprepared = uuid4()
        async with self.sessions() as session:
            await session.execute(
                sa.update(TenantModel)
                .where(TenantModel.id == self.tenants[1])
                .values(status="freeze")
            )
            await session.execute(
                sa.insert(TenantModel).values(
                    id=unprepared,
                    name="No schema",
                    external_id=str(unprepared),
                    status="active",
                )
            )
            await session.commit()
        try:
            async with TenantGate(self.sessions).hold(self.tenants[0], exclusive=True):
                await ensure_trash_cleanup_jobs(self.sessions, self.cutoff)
            self.assertEqual(await self.job_models(), [])
            await ensure_trash_cleanup_jobs(self.sessions, self.cutoff)
            await ensure_trash_cleanup_jobs(self.sessions, self.cutoff)
            self.assertEqual(len(await self.job_models(kind="files.trash.cleanup")), 1)
            async with self.sessions() as session:
                frozen_jobs = list(
                    await session.scalars(
                        sa.select(ScheduledJobModel).where(
                            ScheduledJobModel.tenant_id == self.tenants[1]
                        )
                    )
                )
                self.assertEqual(len(frozen_jobs), 1)
                self.assertFalse(
                    await session.scalar(
                        sa.select(ScheduledJobModel.id).where(
                            ScheduledJobModel.tenant_id == unprepared
                        )
                    )
                )
            await ensure_trash_cleanup_jobs(
                self.sessions, self.cutoff + timedelta(hours=1)
            )
            self.assertEqual(len(await self.job_models(kind="files.trash.cleanup")), 2)
            await ensure_cleanup_jobs(self.sessions, self.cutoff)
            await ensure_cleanup_jobs(self.sessions, self.cutoff)
            self.assertEqual(len(await self.job_models(kind="files.cleanup")), 1)
            file = await self.add_file("gate.pdf", status="purging")
            job = await self.purge_job(file)
            async with TenantGate(self.sessions).hold(self.tenants[0], exclusive=True):
                with self.assertRaises(ScheduledJobDeferred):
                    await self.purge.handle(job)
            async with self.sessions() as session:
                await session.execute(
                    sa.update(TenantModel)
                    .where(TenantModel.id == self.tenants[0])
                    .values(status="deletion_pending")
                )
                await session.commit()
            with self.assertRaises(ScheduledJobDeferred):
                await self.purge.handle(job)
            self.assertIsNotNone(await self.record(file))
        finally:
            async with self.sessions() as session:
                await session.execute(
                    sa.delete(TenantModel).where(TenantModel.id == unprepared)
                )
                await session.commit()

    async def test_shared_worker_retries_recovers_expired_and_exhausted_jobs(
        self,
    ) -> None:
        """Штатный worker повторяет outages, восстанавливает leases и передаёт exhausted в hourly recovery."""
        file = await self.add_file("retry.pdf", status="purging")
        await self.put(file)
        job = await self.purge_job(file)
        worker = ScheduledJobWorker(
            session_factory=self.sessions,
            dispatcher=InMemoryScheduledJobDispatcher({"files.purge": self.purge}),
            process_limit=2,
            recover_limit=100,
            lock_ttl_seconds=300,
            lock_heartbeat_seconds=60,
            retry_base_seconds=1,
            max_attempts=2,
            poll_interval_seconds=1,
            recover_interval_seconds=1,
            heartbeat_path=Path("/tmp/dnk-files-test-heartbeat"),
            concurrency=1,
        )
        with patch.object(
            self.adapter,
            "remove_owned_versions",
            AsyncMock(side_effect=StorageUnavailableError()),
        ):
            await worker._process_job(job)
        self.assertEqual(
            (await self.job_models(kind="files.purge"))[0].status, "scheduled"
        )
        await self.claim(job.id)
        async with self.sessions() as session:
            await session.execute(
                sa.update(ScheduledJobModel)
                .where(ScheduledJobModel.id == job.id)
                .values(locked_until=datetime.now(UTC) - timedelta(seconds=1))
            )
            await session.commit()
        await worker.recover_once()
        self.assertEqual(
            (await self.job_models(kind="files.purge"))[0].status, "failed"
        )
        await self.cleanup.handle(await self.scan_job())
        new_id = (await self.record(file)).purge_job_id
        self.assertNotEqual(new_id, job.id)
        fresh = await self.claim(new_id)
        async with self.sessions() as session:
            await session.execute(
                sa.update(ScheduledJobModel)
                .where(ScheduledJobModel.id == new_id)
                .values(locked_until=datetime.now(UTC) - timedelta(seconds=1))
            )
            await session.commit()
        await worker.recover_once()
        active = next(
            item
            for item in await self.job_models(kind="files.purge")
            if item.id == new_id
        )
        self.assertEqual(active.status, "scheduled")
        await worker._process_job(await self.claim(new_id))
        self.assertIsNone(await self.record(file))
        self.assertEqual(
            next(
                item
                for item in await self.job_models(kind="files.purge")
                if item.id == new_id
            ).status,
            "done",
        )

    async def test_changed_candidate_is_rechecked_under_lock_and_foreign_ids_are_safe(
        self,
    ) -> None:
        """После чтения IDs восстановленный/повторно удалённый файл не очищается раньше срока."""
        file = await self.add_file("race.pdf", status="trashed")
        async with self.session() as session:
            handlers = build_files_handlers(session)
            original = handlers.cleanup_trash._queries.cleanup_candidates

            async def changed(command):
                candidates = await original(command)
                async with self.session() as concurrent:
                    repo = build_files_handlers(concurrent).trash_file._files
                    current = await repo.get_for_update(file.id)
                    # Доменное время до deadline: восстановление и новый цикл между SELECT и lock.
                    current.restore_from_trash(file.purge_after - timedelta(seconds=1))
                    current.move_to_trash(EntityIdVO.from_value(uuid4()), self.cutoff)
                    await repo.save(current)
                    await concurrent.commit()
                return candidates

            with patch.object(
                handlers.cleanup_trash._queries, "cleanup_candidates", changed
            ):
                result = await handlers.cleanup_trash.execute(
                    CleanupExpiredTrashCommand(self.tenants[0], self.cutoff)
                )
                self.assertEqual(result.queued_count, 0)
            await session.commit()
        self.assertEqual((await self.record(file)).status, "trashed")
        foreign = await self.add_file(
            "foreign.pdf",
            tenant=self.tenants[1],
            bucket=self.foreign_bucket,
            status="purging",
        )
        async with self.session() as session:
            await build_files_handlers(session).purge_file.execute(
                PurgeFileCommand(
                    self.tenants[0], foreign.id.uuid, foreign.purge_job_id.uuid
                )
            )
            await session.commit()
        async with self.session(self.tenants[1]) as session:
            self.assertIsNotNone(await session.get(StoredFileModel, foreign.id.uuid))
