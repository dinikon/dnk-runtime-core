"""Ручная очистка корзины на одноразовом PostgreSQL, без внешнего storage I/O."""

from datetime import UTC, datetime, timedelta
import os
import unittest
from unittest.mock import AsyncMock, patch
from uuid import UUID, uuid4, uuid5
from fastapi import Request, Response
from httpx import AsyncClient, ASGITransport
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import async_sessionmaker
from src.config import dnk_config
from src.modules.files.infrastructure.assembly import build_files_handlers
from src.modules.files.infrastructure.persistence.models.stored_file import (
    StoredFileModel,
)
from src.modules.files.infrastructure.stored_file.jobs.purge_queue import (
    ScheduledFilePurgeQueue,
)
from src.modules.files.presentation.jobs.empty_trash import FilesEmptyTrashJobHandler
from src.modules.shared.infrastructure.persistence.global_migrations import (
    GlobalMigrator,
)
from src.modules.shared.infrastructure.jobs.scheduled_job_model import ScheduledJobModel
from src.modules.shared.infrastructure.jobs.sqlalchemy_scheduled_job_repository import (
    SqlAlchemyScheduledJobRepository,
)
from src.modules.shared.infrastructure.persistence.unit_of_work.sqlalchemy import (
    UnitOfWork,
)
from src.modules.shared.application.tokens.token_manager import TokenManager
from src.modules.shared.infrastructure.tokens.in_memory_token_backend import (
    InMemoryTokenBackend,
)
from src.modules.shared.presentation.tokens.depends import TokenManagerDep
from src.modules.identity.presentation.auth.http.csrf import issue_csrf
from src.modules.identity.domain.auth.request_context import RequestContext
from src.modules.tenancy.infrastructure.persistence.tenant import TenantModel
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.files.application.stored_file.command.empty_trash.command import (
    EmptyTrashCommand,
)
from src.modules.files.application.stored_file.command.empty_trash.dto import (
    EmptyTrashCandidateDTO,
)
from test import test_files_read_postgres as support
from test.test_files_mutations_postgres import TestClock
from test import test_files_workers_postgres as worker_support


@unittest.skipUnless(
    os.environ.get("TEST_POSTGRES_URL"), "Disposable PostgreSQL required"
)
class EmptyTrashPostgresTests(unittest.IsolatedAsyncioTestCase):
    """Проверяет HTTP commit, tenant isolation, locks, continuation и rollback очереди."""

    context = support.FilesReadPostgresTests.context
    session = support.FilesReadPostgresTests.session
    add_file = support.FilesReadPostgresTests.add_file
    claim = worker_support.FilesWorkerPostgresTests.claim

    async def asyncSetUp(self) -> None:
        """Создаёт изолированные tenant-схемы, настоящие CSRF и worker lease."""
        await support.FilesReadPostgresTests.asyncSetUp(self)
        async with self.engine.begin() as connection:
            await GlobalMigrator().upgrade(connection)
            for tenant in self.tenants:
                new = f"{dnk_config.SCHEMA_PREFIX}{tenant.hex}"
                await connection.execute(
                    sa.text(f'ALTER SCHEMA "{self.schemas[tenant]}" RENAME TO "{new}"')
                )
                self.schemas[tenant] = new
                await connection.execute(
                    sa.insert(TenantModel).values(
                        id=tenant,
                        name="Empty trash test",
                        external_id=str(tenant),
                        status="active",
                    )
                )
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        self.cutoff = datetime.now(UTC) - timedelta(seconds=1)
        self.clock = TestClock(self.cutoff)
        self.app.state.clock = self.clock
        self.app.state.token_manager = TokenManager(InMemoryTokenBackend())
        await self.client.aclose()
        self.client = AsyncClient(
            transport=ASGITransport(app=self.app, raise_app_exceptions=False),
            base_url="https://files.example",
        )

        @self.app.get("/csrf")
        async def csrf(
            request: Request, response: Response, tokens: TokenManagerDep
        ) -> dict[str, str]:
            """Выдаёт реальный токен, связанный с host и browser session теста."""
            return await issue_csrf(request, response, tokens)

        self.client.cookies.set(
            dnk_config.AUTH.session_cookie_name, "disposable-session"
        )
        token = (await self.client.get("/csrf")).json()["csrf_token"]
        self.headers = {"Origin": "https://files.example", "X-CSRF-Token": token}
        self.worker = FilesEmptyTrashJobHandler(self.sessions)

    async def asyncTearDown(self) -> None:
        """Удаляет только jobs, tenant records и схемы текущего теста."""
        try:
            async with self.engine.begin() as connection:
                await connection.execute(
                    sa.delete(ScheduledJobModel).where(
                        ScheduledJobModel.tenant_id.in_(self.tenants)
                    )
                )
                await connection.execute(
                    sa.delete(TenantModel).where(TenantModel.id.in_(self.tenants))
                )
        finally:
            await support.FilesReadPostgresTests.asyncTearDown(self)

    async def jobs(self, kind: str) -> list[ScheduledJobModel]:
        """Читает только задания текущего tenant и нужного типа."""
        async with self.sessions() as session:
            return list(
                await session.scalars(
                    sa.select(ScheduledJobModel).where(
                        ScheduledJobModel.tenant_id == self.tenants[0],
                        ScheduledJobModel.job_type == kind,
                    )
                )
            )

    async def test_http_security_and_commit_failure(self) -> None:
        """Admin/ACL/CSRF проверяются до UoW; ошибка commit не подтверждает очистку."""
        url = "/api/console/files/trash/"
        self.app.state.context = RequestContext(None, None, None, None)
        self.assertEqual(
            (await self.client.delete(url, headers=self.headers)).status_code, 401
        )
        self.app.state.context = self.context(roles=("member",))
        self.assertEqual(
            (await self.client.delete(url, headers=self.headers)).status_code, 403
        )
        self.app.state.context = self.context()
        auth = AsyncMock()
        auth.can.return_value = False
        self.app.state.authorization_service = auth
        self.assertEqual(
            (await self.client.delete(url, headers=self.headers)).status_code, 403
        )
        auth.can.return_value = True
        self.assertEqual((await self.client.delete(url)).status_code, 403)
        self.assertEqual(self.opened_uows, 0)
        with patch.object(
            UnitOfWork, "commit", side_effect=RuntimeError("commit failed")
        ):
            self.assertEqual(
                (await self.client.delete(url, headers=self.headers)).status_code, 500
            )
        self.assertEqual(await self.jobs("files.trash.empty"), [])
        response = await self.client.delete(url, headers=self.headers)
        self.assertEqual(response.status_code, 202, response.text)
        jobs = await self.jobs("files.trash.empty")
        self.assertEqual(len(jobs), 1)
        self.assertEqual(str(jobs[0].id), response.json()["job_id"])
        self.assertEqual(datetime.fromisoformat(jobs[0].payload["cutoff"]), self.cutoff)
        self.assertEqual(auth.can.await_args.kwargs["resource_id"], None)
        self.assertEqual(auth.can.await_args.kwargs["action"], "files.purge")
        operation = self.app.openapi()["paths"][url]["delete"]
        self.assertNotIn("requestBody", operation)
        self.assertIn("202", operation["responses"])

    async def test_all_disks_pages_snapshot_and_repeat(self) -> None:
        """Проход 105 файлов не зависит от фильтров, не захватывает новые и чужие файлы."""
        files = [
            await self.add_file(
                f"file-{n}.pdf", status="trashed", bucket=self.buckets[n % 3]
            )
            for n in range(105)
        ]
        new = await self.add_file(
            "new.pdf", status="trashed", deleted=self.cutoff + timedelta(seconds=1)
        )
        active = await self.add_file("active.pdf")
        foreign = await self.add_file(
            "foreign.pdf",
            status="trashed",
            tenant=self.tenants[1],
            bucket=self.foreign_bucket,
        )
        response = await self.client.delete(
            "/api/console/files/trash/?search=not-matching&bucket_id="
            + str(self.buckets[0]),
            headers=self.headers,
        )
        self.assertEqual(response.status_code, 202, response.text)
        job = await self.claim(UUID(response.json()["job_id"]))
        await self.worker.handle(job)
        self.assertEqual(len(await self.jobs("files.purge")), 100)
        continuations = [
            record
            for record in await self.jobs("files.trash.empty")
            if record.id != job.id
        ]
        self.assertEqual(len(continuations), 1)
        continuation = continuations[0]
        self.assertEqual(continuation.payload["cutoff"], job.payload["cutoff"])
        self.assertEqual(
            continuation.id, uuid5(job.id, f"after:{continuation.payload['after_id']}")
        )
        await self.worker.handle(await self.claim(continuation.id))
        await self.worker.handle(job)
        self.assertEqual(len(await self.jobs("files.purge")), 105)
        async with self.session() as session:
            rows = list(
                await session.scalars(
                    sa.select(StoredFileModel).where(
                        StoredFileModel.id.in_([f.id.uuid for f in files])
                    )
                )
            )
            self.assertTrue(all(row.status == "purging" for row in rows))
            self.assertEqual(
                (await session.get(StoredFileModel, new.id.uuid)).status, "trashed"
            )
            self.assertEqual(
                (await session.get(StoredFileModel, active.id.uuid)).status, "ready"
            )
        async with self.session(self.tenants[1]) as session:
            self.assertEqual(
                (await session.get(StoredFileModel, foreign.id.uuid)).status, "trashed"
            )

    async def test_batch_continuation_rolls_back_with_file_transitions(self) -> None:
        """Ошибка continuation откатывает все состояния и purge jobs текущей порции."""
        for n in range(101):
            await self.add_file(f"rollback-{n}.pdf", status="trashed")
        response = await self.client.delete(
            "/api/console/files/trash/", headers=self.headers
        )
        job = await self.claim(UUID(response.json()["job_id"]))
        original = ScheduledFilePurgeQueue.schedule_empty

        async def fail(
            queue: ScheduledFilePurgeQueue, *args: object, **kwargs: object
        ) -> None:
            """Имитирует сбой после INSERT continuation в той же транзакции."""
            await original(queue, *args, **kwargs)
            raise RuntimeError("continuation failed")

        with patch.object(ScheduledFilePurgeQueue, "schedule_empty", fail):
            with self.assertRaises(RuntimeError):
                await self.worker.handle(job)
        self.assertEqual(await self.jobs("files.purge"), [])
        self.assertEqual(len(await self.jobs("files.trash.empty")), 1)
        async with self.session() as session:
            self.assertEqual(
                set(await session.scalars(sa.select(StoredFileModel.status))),
                {"trashed"},
            )
        await self.worker.handle(job)
        self.assertEqual(len(await self.jobs("files.purge")), 100)

    async def test_stale_lease_does_not_mutate_and_lost_lease_rolls_back(self) -> None:
        """Чужая или потерянная lease не позволяет фиксировать порцию очистки."""
        await self.add_file("lease.pdf", status="trashed")
        response = await self.client.delete(
            "/api/console/files/trash/", headers=self.headers
        )
        job = await self.claim(UUID(response.json()["job_id"]))
        from dataclasses import replace

        await self.worker.handle(replace(job, lock_token="stale"))
        self.assertEqual(await self.jobs("files.purge"), [])
        from src.modules.shared.application.jobs.scheduled_job_deferred import (
            ScheduledJobDeferred,
        )

        with patch.object(
            SqlAlchemyScheduledJobRepository,
            "owns_current_lease",
            side_effect=[True, False],
        ):
            with self.assertRaises(ScheduledJobDeferred):
                await self.worker.handle(job)
        self.assertEqual(await self.jobs("files.purge"), [])
        await self.worker.handle(job)
        self.assertEqual(len(await self.jobs("files.purge")), 1)

    async def test_restore_and_retrash_after_projection_are_skipped(self) -> None:
        """После SQL-проекции новый lock читает committed восстановление и новое удаление."""
        restored = await self.add_file("restored.pdf", status="trashed")
        retrash = await self.add_file("retrash.pdf", status="trashed")
        await self.add_file("eligible.pdf", status="trashed")
        async with self.session() as session:
            handlers = build_files_handlers(session)
            queries = handlers.empty_trash._queries
            original = queries.empty_trash_candidates

            async def changed(
                command: EmptyTrashCommand,
            ) -> tuple[EmptyTrashCandidateDTO, ...]:
                """Меняет два агрегата отдельной транзакцией после чтения ID."""
                candidates = await original(command)
                async with self.session() as concurrent:
                    concurrent_handlers = build_files_handlers(concurrent)
                    files = concurrent_handlers.empty_trash._files
                    for item in (restored, retrash):
                        file = await files.get_for_update(item.id)
                        file.restore_from_trash(self.cutoff + timedelta(seconds=1))
                        if item is retrash:
                            file.move_to_trash(
                                EntityIdVO.from_value(uuid4()),
                                self.cutoff + timedelta(seconds=2),
                            )
                        await files.save(file)
                    await concurrent.commit()
                return candidates

            with patch.object(queries, "empty_trash_candidates", changed):
                result = await handlers.empty_trash.execute(
                    EmptyTrashCommand(self.tenants[0], self.cutoff)
                )
            await session.commit()
            self.assertEqual(result.queued_count, 1)
            self.assertEqual(
                (await session.get(StoredFileModel, restored.id.uuid)).status, "ready"
            )
            self.assertEqual(
                (await session.get(StoredFileModel, retrash.id.uuid)).status, "trashed"
            )
        self.assertEqual(len(await self.jobs("files.purge")), 1)
