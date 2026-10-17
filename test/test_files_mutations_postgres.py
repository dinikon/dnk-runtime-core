"""HTTP-мутации Files на настоящих PostgreSQL/MinIO с общей транзакцией и CSRF."""

import asyncio
from datetime import UTC, datetime, timedelta
from io import BytesIO
import os
from typing import Any
import unittest
from unittest.mock import AsyncMock, patch
from uuid import UUID, uuid4

from fastapi import Request, Response
from sqlalchemy import select, delete, update

from src.config import dnk_config
from src.modules.files.infrastructure.assembly import build_files_handlers
from src.modules.files.infrastructure.storage.minio_adapter import MinioStorageAdapter
from src.modules.files.infrastructure.storage.resolver import StorageResolver
from src.modules.files.application.port.storage import (
    StorageLocation,
    StorageUnavailableError,
    StorageOwnershipError,
)
from src.modules.files.application.stored_file.command.request_file_purge.command import (
    RequestFilePurgeCommand,
)
from src.modules.files.infrastructure.persistence.models.stored_file import (
    StoredFileModel,
)
from src.modules.files.infrastructure.persistence.models.bucket import BucketModel
from src.modules.files.infrastructure.stored_file.jobs.purge_queue import (
    ScheduledFilePurgeQueue,
)
from src.modules.files.presentation.stored_file.multipart import (
    get_console_upload_limit,
)
from src.modules.shared.infrastructure.jobs.scheduled_job_model import ScheduledJobModel
from src.modules.shared.infrastructure.persistence.global_migrations import (
    GlobalMigrator,
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
from src.modules.identity.application.access.authorization_service_protocol import (
    AuthorizationServiceProtocol,
)
from test import test_files_read_postgres as support


class TestClock:
    """Управляемые часы для проверки срока без ожидания."""

    def __init__(self, value: datetime) -> None:
        """Сохраняет текущее UTC-время теста."""
        self.value = value

    def now(self) -> datetime:
        """Возвращает установленное время."""
        return self.value


@unittest.skipUnless(
    os.environ.get("TEST_POSTGRES_URL") and os.environ.get("TEST_MINIO_ENDPOINT"),
    "Disposable services required",
)
class FilesMutationPostgresTests(unittest.IsolatedAsyncioTestCase):
    """Проверяет commit/rollback HTTP и owned-объекты в одноразовых сервисах."""

    context = support.FilesReadPostgresTests.context
    session = support.FilesReadPostgresTests.session
    add_file = support.FilesReadPostgresTests.add_file
    get = support.FilesReadPostgresTests.get

    async def asyncSetUp(self) -> None:
        """Переиспользует изолированные схемы и подключает owned-бакеты и настоящий CSRF."""
        await support.FilesReadPostgresTests.asyncSetUp(self)
        self.adapter = MinioStorageAdapter(dnk_config.FILES)
        self.resolver = StorageResolver(
            {("minio", "system_minio"): lambda: self.adapter}
        )
        self.locations: list[StorageLocation] = []
        for tenant, bucket in (
            (self.tenants[0], self.buckets[0]),
            (self.tenants[1], self.foreign_bucket),
        ):
            async with self.session(tenant) as session:
                await session.execute(
                    update(BucketModel)
                    .where(BucketModel.id == bucket)
                    .values(name=f"dnk-tenant-{tenant.hex}")
                )
                await session.commit()
            location = StorageLocation(
                tenant, bucket, f"dnk-tenant-{tenant.hex}", "minio", "system_minio"
            )
            await self.adapter.ensure_private_bucket(location)
            self.locations.append(location)
        async with self.engine.begin() as connection:
            await GlobalMigrator().upgrade(connection)
        self.clock = TestClock(datetime.now(UTC) + timedelta(seconds=1))
        self.now = self.clock.now()
        self.app.state.clock = self.clock
        self.app.state.token_manager = TokenManager(InMemoryTokenBackend())
        self.storage_patch = patch(
            "src.modules.files.infrastructure.assembly.get_storage_resolver",
            return_value=self.resolver,
        )
        self.storage_patch.start()

        @self.app.get("/csrf")
        async def csrf(
            request: Request, response: Response, tokens: TokenManagerDep
        ) -> dict[str, str]:
            """Выдаёт реальный session/flow-bound CSRF token для тестового браузера."""
            return await issue_csrf(request, response, tokens)

        self.client.base_url = (
            "http" if dnk_config.AUTH.allow_insecure_http else "https"
        ) + "://files.example"
        token = (await self.client.get("/csrf")).json()["csrf_token"]
        self.headers = {
            "origin": ("http" if dnk_config.AUTH.allow_insecure_http else "https")
            + "://files.example",
            "x-csrf-token": token,
        }

    async def asyncTearDown(self) -> None:
        """Удаляет только тестовые jobs, owned-бакеты и схемы."""
        self.storage_patch.stop()
        try:
            for location in self.locations:
                await self.adapter.purge(location)
            async with self.engine.begin() as connection:
                await connection.execute(
                    delete(ScheduledJobModel).where(
                        ScheduledJobModel.tenant_id.in_(self.tenants)
                    )
                )
        finally:
            await support.FilesReadPostgresTests.asyncTearDown(self)

    async def upload(
        self,
        content: bytes = b"content",
        name: str = "report.pdf",
        *,
        bucket: UUID | None = None,
    ) -> dict[str, Any]:
        """Отправляет файл с реальным CSRF и проверяет HTTP-подтверждение после commit."""
        response = await self.client.post(
            "/api/console/files/items/",
            headers=self.headers,
            files={"file": (name, content, "application/pdf")},
            data={"bucket_id": str(bucket)} if bucket else None,
        )
        self.assertEqual(response.status_code, 201, response.text)
        self.clock.value = max(
            self.clock.value, datetime.now(UTC) + timedelta(seconds=1)
        )
        return response.json()

    async def mutate(self, method: str, path: str, status: int = 200) -> Any:
        """Проверяет ожидаемый HTTP-статус файловой мутации."""
        response = await self.client.request(
            method, "/api/console/files/" + path, headers=self.headers
        )
        self.assertEqual(response.status_code, status, response.text)
        return response

    async def row(self, identifier: UUID) -> StoredFileModel:
        """Возвращает committed-представление в новой SQL-сессии теста."""
        async with self.session() as session:
            return await session.get(StoredFileModel, identifier)

    async def test_upload_empty_duplicate_names_exact_limit_and_no_content_length(
        self,
    ) -> None:
        """Пустой файл и точный лимит принимаются; одинаковые имена не перезаписываются."""
        empty = await self.upload(b"", bucket=self.buckets[0])
        self.assertEqual(empty["size_bytes"], 0)
        with patch.dict(
            self.app.dependency_overrides, {get_console_upload_limit: lambda: 4}
        ):
            first = await self.upload(b"1234", "same.pdf")
            second = await self.upload(b"5678", "same.pdf")
            self.assertNotEqual(first["file_id"], second["file_id"])
            too_big = await self.client.post(
                "/api/console/files/items/",
                headers=self.headers,
                files={"file": ("x.pdf", b"12345", "application/pdf")},
            )
            self.assertEqual(too_big.status_code, 413)
            boundary = "bounded-file-test"
            body = (
                f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="chunk.pdf"\r\n\r\n'.encode()
                + b"1234"
                + f"\r\n--{boundary}--\r\n".encode()
            )

            async def chunks() -> Any:
                """Передаёт тело без Content-Length маленькими порциями."""
                for start in range(0, len(body), 7):
                    yield body[start : start + 7]

            response = await self.client.post(
                "/api/console/files/items/",
                headers={
                    **self.headers,
                    "content-type": f"multipart/form-data; boundary={boundary}",
                },
                content=chunks(),
            )
            self.assertEqual(response.status_code, 201, response.text)
            self.assertEqual(
                response.json()["content_type"], "application/octet-stream"
            )
        for data, content in ((first, b"1234"), (second, b"5678")):
            record = await self.row(UUID(data["file_id"]))
            stream = await self.adapter.open(self.locations[0], record.object_key)
            try:
                self.assertEqual(b"".join([chunk async for chunk in stream]), content)
            finally:
                await stream.aclose()
        self.assertEqual((await self.get("items"))["total"], 4)

    async def test_trash_restore_cycle_and_purge_job_are_idempotent(self) -> None:
        """Переходы меняют списки; повтор trash/purge сохраняет даты/job, объект не удаляется."""
        data = await self.upload()
        identifier = UUID(data["file_id"])
        trash = (await self.mutate("DELETE", f"items/{identifier}/")).json()
        self.assertEqual(
            datetime.fromisoformat(trash["purge_after"].replace("Z", "+00:00"))
            - datetime.fromisoformat(trash["deleted_at"].replace("Z", "+00:00")),
            timedelta(days=30),
        )
        self.clock.value += timedelta(hours=1)
        self.assertEqual(
            (await self.mutate("DELETE", f"items/{identifier}/")).json(), trash
        )
        row = await self.row(identifier)
        self.assertEqual(str(row.deleted_by), self.app.state.context.principal.user_id)
        self.assertEqual((await self.get("items"))["total"], 0)
        self.assertEqual((await self.get("trash"))["total"], 1)
        restored = (await self.mutate("POST", f"items/{identifier}/restore/")).json()
        self.assertEqual(restored, {"file_id": str(identifier), "status": "ready"})
        await self.mutate("POST", f"items/{identifier}/restore/")
        self.clock.value += timedelta(hours=1)
        later = (await self.mutate("DELETE", f"items/{identifier}/")).json()
        self.assertNotEqual(trash["deleted_at"], later["deleted_at"])
        accepted = await self.mutate("DELETE", f"trash/{identifier}/", 202)
        self.assertEqual(accepted.content, b"")
        row = await self.row(identifier)
        previous = (
            row.purge_job_id,
            row.purge_requested_at,
            row.deleted_at,
            row.purge_after,
        )
        self.clock.value += timedelta(minutes=1)
        await self.mutate("DELETE", f"trash/{identifier}/", 202)
        row = await self.row(identifier)
        self.assertEqual(
            (row.purge_job_id, row.purge_requested_at, row.deleted_at, row.purge_after),
            previous,
        )
        async with self.engine.connect() as connection:
            jobs = (
                (
                    await connection.execute(
                        select(ScheduledJobModel).where(
                            ScheduledJobModel.tenant_id == self.tenants[0]
                        )
                    )
                )
                .mappings()
                .all()
            )
        self.assertEqual(len(jobs), 1)
        job = jobs[0]
        self.assertEqual(
            job["payload"],
            {
                "tenant_id": str(self.tenants[0]),
                "file_id": str(identifier),
                "job_id": str(row.purge_job_id),
            },
        )
        self.assertEqual(
            (job["id"], job["job_type"], job["status"]),
            (row.purge_job_id, "files.purge", "scheduled"),
        )
        self.assertTrue(
            await self.adapter.exists_owned(self.locations[0], row.object_key)
        )
        await self.mutate("POST", f"items/{identifier}/restore/", 409)
        await self.mutate("DELETE", f"items/{identifier}/", 409)

    async def test_restore_boundary_missing_object_storage_outage_and_ownership(
        self,
    ) -> None:
        """Ошибки срока/storage/ownership не сохраняют ложное восстановление."""
        data = await self.upload()
        identifier = UUID(data["file_id"])
        await self.mutate("DELETE", f"items/{identifier}/")
        for error, status in (
            (StorageUnavailableError("unavailable"), 503),
            (StorageOwnershipError("unowned"), 409),
        ):
            with patch.object(
                self.adapter, "exists_owned", AsyncMock(side_effect=error)
            ):
                await self.mutate("POST", f"items/{identifier}/restore/", status)
            self.assertEqual((await self.row(identifier)).status, "trashed")
        row = await self.row(identifier)

        async def delayed_check(*args: object) -> bool:
            """Имитирует истечение срока во время проверки объекта storage."""
            self.clock.value = row.purge_after
            return True

        with patch.object(
            self.adapter, "exists_owned", AsyncMock(side_effect=delayed_check)
        ):
            await self.mutate("POST", f"items/{identifier}/restore/", 409)
        self.assertEqual((await self.row(identifier)).status, "trashed")
        self.clock.value = row.purge_after
        with patch.object(self.adapter, "exists_owned", AsyncMock()) as check:
            await self.mutate("POST", f"items/{identifier}/restore/", 409)
            check.assert_not_awaited()
        self.clock.value = row.purge_after - timedelta(microseconds=1)
        await self.mutate("POST", f"items/{identifier}/restore/")
        await self.mutate("DELETE", f"items/{identifier}/")
        row = await self.row(identifier)
        await self.adapter.remove(self.locations[0], row.object_key)
        await self.mutate("POST", f"items/{identifier}/restore/", 409)
        self.assertEqual((await self.row(identifier)).status, "trashed")

    async def test_unknown_foreign_files_unready_disks_and_invalid_upload_metadata(
        self,
    ) -> None:
        """Чужие ID не отличаются от неизвестных; неготовые диски и плохие metadata отвергаются."""
        foreign = await self.add_file(
            "foreign.pdf", tenant=self.tenants[1], bucket=self.foreign_bucket
        )
        for identifier in (uuid4(), foreign.id.uuid):
            for method, path in [
                ("DELETE", f"items/{identifier}/"),
                ("POST", f"items/{identifier}/restore/"),
                ("DELETE", f"trash/{identifier}/"),
            ]:
                await self.mutate(method, path, 404)
        for bucket, status in (
            (self.foreign_bucket, 404),
            (uuid4(), 404),
            (self.buckets[2], 409),
        ):
            response = await self.client.post(
                "/api/console/files/items/",
                headers=self.headers,
                data={"bucket_id": str(bucket)},
                files={"file": ("x.pdf", b"x", "application/pdf")},
            )
            self.assertEqual(response.status_code, status)
        for name, mime in (("../x.pdf", "application/pdf"), ("x.pdf", "invalid")):
            response = await self.client.post(
                "/api/console/files/items/",
                headers=self.headers,
                files={"file": (name, b"x", mime)},
            )
            self.assertEqual(response.status_code, 422, response.text)
        self.assertEqual((await self.get("items"))["total"], 0)

    async def test_admin_csrf_and_action_authorization_precede_database_and_upload(
        self,
    ) -> None:
        """Каждый метод проверяет роль, отдельный action/resource и настоящий CSRF."""
        identifier = uuid4()
        operations = [
            (
                "POST",
                "items/",
                "upload",
                {"files": {"file": ("x.pdf", b"x", "application/pdf")}},
            ),
            ("DELETE", f"items/{identifier}/", "trash", {}),
            ("POST", f"items/{identifier}/restore/", "restore", {}),
            ("DELETE", f"trash/{identifier}/", "purge", {}),
        ]
        for context, status in (
            (self.context(roles=("member",)), 403),
            (RequestContext(None, None, None, None), 401),
        ):
            self.app.state.context = context
            for method, path, action, kwargs in operations:
                response = await self.client.request(
                    method, "/api/console/files/" + path, headers=self.headers, **kwargs
                )
                self.assertEqual(response.status_code, status)
        self.app.state.context = self.context()
        for method, path, action, kwargs in operations:
            for headers in (
                {},
                {**self.headers, "origin": "http://other.example"},
                {**self.headers, "x-csrf-token": "invalid"},
            ):
                response = await self.client.request(
                    method, "/api/console/files/" + path, headers=headers, **kwargs
                )
                self.assertEqual(response.status_code, 403)
        self.assertEqual(self.opened_uows, 0)
        service = AsyncMock(spec=AuthorizationServiceProtocol)
        service.can.return_value = False
        self.app.state.authorization_service = service
        for method, path, action, kwargs in operations:
            response = await self.client.request(
                method, "/api/console/files/" + path, headers=self.headers, **kwargs
            )
            self.assertEqual(response.status_code, 403)
            service.can.assert_awaited_with(
                user_id=UUID(self.app.state.context.principal.user_id),
                tenant_id=self.tenants[0],
                action="files." + action,
                resource_type="stored_file",
                resource_id=None if action == "upload" else identifier,
            )
        self.assertEqual(self.opened_uows, 0)

    async def test_queue_and_commit_failure_roll_back_file_and_job(self) -> None:
        """Сбой после INSERT job или на commit не оставляет purging и не возвращает 202."""
        data = await self.upload()
        identifier = UUID(data["file_id"])
        await self.mutate("DELETE", f"items/{identifier}/")
        actual_schedule = ScheduledFilePurgeQueue.schedule

        async def failed_schedule(queue: ScheduledFilePurgeQueue, *args: Any) -> None:
            """Имитирует сбой после записи job в той же транзакции."""
            await actual_schedule(queue, *args)
            raise RuntimeError("queue boundary failed")

        with patch.object(ScheduledFilePurgeQueue, "schedule", failed_schedule):
            with self.assertRaises(RuntimeError):
                await self.client.delete(
                    f"/api/console/files/trash/{identifier}/", headers=self.headers
                )
        self.assertEqual((await self.row(identifier)).status, "trashed")
        async with self.engine.connect() as connection:
            self.assertEqual(
                (
                    await connection.execute(
                        select(ScheduledJobModel.id).where(
                            ScheduledJobModel.tenant_id == self.tenants[0]
                        )
                    )
                ).all(),
                [],
            )
        with patch.object(
            UnitOfWork, "commit", AsyncMock(side_effect=RuntimeError("commit failed"))
        ):
            with self.assertRaises(RuntimeError):
                await self.client.delete(
                    f"/api/console/files/trash/{identifier}/", headers=self.headers
                )
        self.assertEqual((await self.row(identifier)).status, "trashed")
        async with self.engine.connect() as connection:
            self.assertEqual(
                (
                    await connection.execute(
                        select(ScheduledJobModel.id).where(
                            ScheduledJobModel.tenant_id == self.tenants[0]
                        )
                    )
                ).all(),
                [],
            )

    async def test_concurrent_purge_requests_share_one_locked_job(self) -> None:
        """Два concurrent caller под lock создают единственную purge job."""
        data = await self.upload()
        identifier = UUID(data["file_id"])
        await self.mutate("DELETE", f"items/{identifier}/")

        async def request() -> None:
            """Открывает независимый внешний UoW для конкурентного запроса."""
            async with self.engine.connect() as connection:
                await connection.execution_options(
                    schema_translate_map={"tenant": self.schemas[self.tenants[0]]}
                )
                from sqlalchemy.ext.asyncio import async_sessionmaker

                async with UnitOfWork(
                    async_sessionmaker(connection, expire_on_commit=False)
                ) as uow:
                    await build_files_handlers(
                        uow.session, self.resolver, clock=self.clock
                    ).request_purge.execute(
                        RequestFilePurgeCommand(self.tenants[0], identifier, uuid4())
                    )

        await asyncio.gather(request(), request())
        async with self.engine.connect() as connection:
            jobs = (
                await connection.execute(
                    select(ScheduledJobModel.id).where(
                        ScheduledJobModel.tenant_id == self.tenants[0]
                    )
                )
            ).all()
        self.assertEqual(jobs, [((await self.row(identifier)).purge_job_id,)])

    async def test_minio_stat_checks_bucket_and_object_ownership(self) -> None:
        """Реальный stat не принимает объект с потерянными или чужими ownership metadata."""
        key = uuid4().hex
        self.assertFalse(await self.adapter.exists_owned(self.locations[0], key))
        await self.adapter.call(
            lambda: self.adapter._client.put_object(
                self.locations[0].bucket_name, key, BytesIO(b"x"), 1
            )
        )
        with self.assertRaises(StorageOwnershipError):
            await self.adapter.exists_owned(self.locations[0], key)
        data = await self.upload()
        row = await self.row(UUID(data["file_id"]))
        self.assertTrue(
            await self.adapter.exists_owned(self.locations[0], row.object_key)
        )
        with self.assertRaises(StorageOwnershipError):
            await self.adapter.exists_owned(
                self.locations[1], row.object_key + "/invalid"
            )

    async def test_openapi_and_multipart_reject_untrusted_or_duplicate_fields(
        self,
    ) -> None:
        """Контракты описывают multipart и отдельные ответы; лишние/повторные поля не принимаются."""
        paths = self.app.openapi()["paths"]
        upload = paths["/api/console/files/items/"]["post"]
        self.assertEqual(set(upload["requestBody"]["content"]), {"multipart/form-data"})
        properties = upload["requestBody"]["content"]["multipart/form-data"]["schema"][
            "properties"
        ]
        self.assertEqual(set(properties), {"file", "bucket_id"})
        self.assertEqual(
            properties["file"]["contentMediaType"], "application/octet-stream"
        )
        self.assertEqual(
            upload["responses"]["201"]["content"]["application/json"]["schema"]["$ref"],
            "#/components/schemas/UploadFileResponse",
        )
        purge = paths["/api/console/files/trash/{file_id}/"]["delete"]
        self.assertNotIn("content", purge["responses"]["202"])
        for path, method in (
            ("/api/console/files/items/{file_id}/", "delete"),
            ("/api/console/files/items/{file_id}/restore/", "post"),
            ("/api/console/files/trash/{file_id}/", "delete"),
        ):
            self.assertNotIn("requestBody", paths[path][method])
        for form in (
            {"tenant_id": str(self.tenants[1])},
            {"actor_id": str(uuid4())},
            {"object_key": uuid4().hex},
            {"bucket_id": "invalid"},
        ):
            response = await self.client.post(
                "/api/console/files/items/",
                headers=self.headers,
                data=form,
                files={"file": ("x.pdf", b"x", "application/pdf")},
            )
            self.assertEqual(response.status_code, 422, response.text)
        response = await self.client.post(
            "/api/console/files/items/",
            headers=self.headers,
            files=[("file", ("x.pdf", b"x")), ("file", ("y.pdf", b"y"))],
        )
        self.assertEqual(response.status_code, 422)
