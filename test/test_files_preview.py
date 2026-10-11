"""Предпросмотр: роль admin, tenant, MIME, HTTP-контракт и освобождение потока."""

import asyncio
from collections.abc import AsyncIterator
import threading
import unittest
from unittest.mock import AsyncMock, Mock, patch
from urllib.parse import quote
from uuid import UUID, uuid4

from anyio import CancelScope
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from starlette.requests import ClientDisconnect

from src.config.infrastructure.files_config import FilesSettings
from src.modules.files.application.port.query_repository import (
    FileContentLocationDTO,
    StorageQueryRepositoryProtocol,
)
from src.modules.files.application.port.storage import (
    StorageAdapterProtocol,
    StorageLocation,
    StorageOwnershipError,
    StorageResolverProtocol,
    StorageUnavailableError,
)
from src.modules.files.application.stored_file.error import UnsupportedFilePreviewError
from src.modules.files.application.stored_file.query.get_file_preview.dto import (
    GetFilePreviewResultDTO,
)
from src.modules.files.application.stored_file.query.get_file_preview.handler import (
    GetFilePreviewHandler,
    PREVIEW_MEDIA_TYPES,
    PREVIEW_TEXT_TYPES,
)
from src.modules.files.application.stored_file.query.get_file_preview.query import (
    GetFilePreviewQuery,
)
from src.modules.files.domain.error import FileNotFoundError
from src.modules.files.infrastructure.storage.minio_adapter import (
    MinioFileContentStream,
    MinioStorageAdapter,
)
from src.modules.files.presentation.router import router
from src.modules.files.presentation.stored_file.depends import (
    get_get_file_preview_handler,
)
from src.modules.files.presentation.stored_file.http.response.get_file_preview import (
    GetFilePreviewResponse,
)
from src.modules.identity.application.access.authorization_service_protocol import (
    AuthorizationServiceProtocol,
)
from src.modules.identity.domain.auth.principal import Principal
from src.modules.identity.domain.auth.request_context import RequestContext
from src.modules.identity.presentation.auth.depends import get_optional_request_context
from src.modules.shared.presentation.persistence.depends import UoWDep, get_uow


class PreviewTestStream:
    """Передаёт небольшие порции и фиксирует закрытие без SDK и DB."""

    def __init__(self, *, fail: bool = False) -> None:
        """Готовит поток, который может оборваться после первой порции."""
        self.fail = fail
        self.closed = 0
        self.iterated = 0

    async def __aiter__(self) -> AsyncIterator[bytes]:
        """Выдаёт две порции с необязательной ошибкой чтения."""
        self.iterated += 1
        yield b"%PDF-"
        if self.fail:
            raise StorageUnavailableError("private SDK details")
        yield b"test"

    async def aclose(self) -> None:
        """Фиксирует освобождение ресурса для проверок всех границ ответа."""
        self.closed += 1


class FilePreviewTests(unittest.IsolatedAsyncioTestCase):
    """Проверяет use case и реальный HTTP router без внешних сервисов."""

    async def asyncSetUp(self) -> None:
        """Собирает порты и HTTP-приложение с настоящей admin dependency."""
        self.tenant, self.file_id, self.bucket = uuid4(), uuid4(), uuid4()
        self.stream = PreviewTestStream()
        self.location = StorageLocation(
            self.tenant,
            self.bucket,
            f"dnk-tenant-{self.tenant.hex}",
            "minio",
            "system_minio",
        )
        self.projection = FileContentLocationDTO(
            self.location, self.file_id.hex, 'Отчёт "2026".pdf', "application/pdf", 9
        )
        self.repository = AsyncMock(spec=StorageQueryRepositoryProtocol)
        self.repository.content_location.return_value = self.projection
        self.adapter = AsyncMock(spec=StorageAdapterProtocol)
        self.adapter.exists_owned.return_value = True
        self.adapter.open.return_value = self.stream
        self.resolver = Mock(spec=StorageResolverProtocol)
        self.resolver.resolve.return_value = self.adapter
        self.handler = GetFilePreviewHandler(self.repository, self.resolver)
        self.authorization = AsyncMock(spec=AuthorizationServiceProtocol)
        self.authorization.can.return_value = True
        self.opened_uows = 0
        self.commit_failed = False
        self.app = FastAPI()
        self.app.include_router(router, prefix="/api/console")
        self.app.state.context = self.context()
        self.app.state.authorization_service = self.authorization
        self.app.dependency_overrides[get_optional_request_context] = (
            lambda: self.app.state.context
        )

        async def uow() -> AsyncIterator[Mock]:
            """Имитирует внешнюю границу UoW и ошибку commit до отправки ответа."""
            self.opened_uows += 1
            yield Mock()
            if self.commit_failed:
                raise RuntimeError("Commit failed")

        def handler(_uow: UoWDep) -> GetFilePreviewHandler:
            """Сохраняет зависимость handler от function-scoped UoW."""
            return self.handler

        self.app.dependency_overrides[get_uow] = uow
        self.app.dependency_overrides[get_get_file_preview_handler] = handler
        self.client = AsyncClient(
            transport=ASGITransport(app=self.app, raise_app_exceptions=False),
            base_url="https://files.example",
        )
        self.url = f"/api/console/files/items/{self.file_id}/preview/"

    async def asyncTearDown(self) -> None:
        """Закрывает тестовый HTTP-клиент."""
        await self.client.aclose()

    def context(self, roles: tuple[str, ...] = ("admin",)) -> RequestContext:
        """Возвращает trusted principal тестового tenant."""
        return RequestContext(
            Principal(str(uuid4()), str(self.tenant), "test", roles), None, None, None
        )

    async def test_admin_receives_inline_stream_and_resource_authorization(
        self,
    ) -> None:
        """Успех передаёт точные bytes, безопасное Unicode-имя и file-specific ACL."""
        response = await self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"%PDF-test")
        self.assertEqual(response.headers["content-type"], "application/pdf")
        self.assertEqual(response.headers["content-length"], "9")
        self.assertEqual(
            response.headers["content-disposition"],
            f"inline; filename*=UTF-8''{quote(self.projection.name, safe='')}",
        )
        self.assertEqual(response.headers["cache-control"], "private, no-store")
        self.assertEqual(response.headers["x-content-type-options"], "nosniff")
        self.assertIn("sandbox", response.headers["content-security-policy"])
        self.assertIn(
            "frame-ancestors 'self'", response.headers["content-security-policy"]
        )
        self.assertEqual(self.stream.closed, 1)
        self.repository.content_location.assert_awaited_once_with(
            self.tenant, self.file_id
        )
        self.authorization.can.assert_awaited_once_with(
            user_id=UUID(self.app.state.context.principal.user_id),
            tenant_id=self.tenant,
            action="files.read",
            resource_type="stored_file",
            resource_id=self.file_id,
        )

    async def test_anonymous_member_and_missing_tenant_never_open_uow(self) -> None:
        """Роль admin проверяется даже при allow-all до DB и storage."""
        cases = [
            (RequestContext(None, None, None, None), 401),
            (self.context(("member",)), 403),
            (self.context(("administrator",)), 403),
            (self.context(()), 403),
            (
                RequestContext(
                    Principal(str(uuid4()), None, "test", ("admin",)), None, None, None
                ),
                403,
            ),
        ]
        for context, status in cases:
            self.app.state.context = context
            self.assertEqual((await self.client.get(self.url)).status_code, status)
        self.assertEqual(self.opened_uows, 0)
        self.repository.content_location.assert_not_awaited()
        self.adapter.open.assert_not_awaited()

    async def test_additional_authorization_denial_precedes_database(self) -> None:
        """Admin без разрешения читать данный файл получает 403 до UoW."""
        self.authorization.can.return_value = False
        self.assertEqual((await self.client.get(self.url)).status_code, 403)
        self.assertEqual(self.opened_uows, 0)
        self.adapter.open.assert_not_awaited()

    async def test_supported_mime_normalization_and_plain_text_projection(self) -> None:
        """Все разрешённые MIME нормализуются; JSON/CSV/Markdown выдаются как текст."""
        from dataclasses import replace

        for mime in sorted(PREVIEW_MEDIA_TYPES | PREVIEW_TEXT_TYPES):
            with self.subTest(mime=mime):
                self.repository.content_location.return_value = replace(
                    self.projection, content_type=f" {mime.upper()}; charset=UTF-8 "
                )
                result = await self.handler.execute(
                    GetFilePreviewQuery(self.tenant, self.file_id)
                )
                self.assertIsInstance(result, GetFilePreviewResultDTO)
                self.assertEqual(
                    result.content_type,
                    "text/plain; charset=utf-8" if mime in PREVIEW_TEXT_TYPES else mime,
                )
                self.assertIs(result.stream, self.stream)

    async def test_active_and_unknown_formats_are_rejected_before_storage(self) -> None:
        """HTML/SVG/XML, Office, архивы и generic bytes не получают inline-выдачу."""
        from dataclasses import replace

        for mime in (
            "text/html",
            "image/svg+xml",
            "application/xml",
            "application/zip",
            "application/octet-stream",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ):
            self.repository.content_location.return_value = replace(
                self.projection, content_type=mime
            )
            with self.assertRaises(UnsupportedFilePreviewError):
                await self.handler.execute(
                    GetFilePreviewQuery(self.tenant, self.file_id)
                )
            self.assertEqual((await self.client.get(self.url)).status_code, 415)
        self.resolver.resolve.assert_not_called()

    async def test_missing_foreign_unready_and_trashed_projection_is_not_opened(
        self,
    ) -> None:
        """Отсутствующая ready-проекция скрывает все недоступные записи одинаковым 404."""
        self.repository.content_location.return_value = None
        foreign = uuid4()
        self.assertEqual(
            (
                await self.client.get(f"/api/console/files/items/{foreign}/preview/")
            ).status_code,
            404,
        )
        with self.assertRaises(FileNotFoundError):
            await self.handler.execute(GetFilePreviewQuery(self.tenant, self.file_id))
        self.resolver.resolve.assert_not_called()

    async def test_absent_owned_object_and_storage_errors_have_safe_http_statuses(
        self,
    ) -> None:
        """Потерянный объект — 404; ownership — 409; outage — 503 без SDK details."""
        self.adapter.exists_owned.return_value = False
        self.assertEqual((await self.client.get(self.url)).status_code, 404)
        self.adapter.open.assert_not_awaited()
        for error, status in (
            (StorageOwnershipError("secret SDK response"), 409),
            (StorageUnavailableError("secret SDK response"), 503),
        ):
            self.adapter.exists_owned.side_effect = error
            response = await self.client.get(self.url)
            self.assertEqual(response.status_code, status)
            self.assertNotIn("secret", response.text)
        self.adapter.open.assert_not_awaited()

    async def test_commit_and_response_construction_failure_close_unread_stream(
        self,
    ) -> None:
        """Ошибка до отправки не оставляет открытого потока и не выдаёт ложный успех."""
        self.commit_failed = True
        self.assertEqual((await self.client.get(self.url)).status_code, 500)
        self.assertEqual(self.stream.iterated, 0)
        self.assertEqual(self.stream.closed, 1)
        self.commit_failed = False
        self.stream = PreviewTestStream()
        self.adapter.open.return_value = self.stream
        with patch.object(
            GetFilePreviewResponse, "from_dto", side_effect=RuntimeError()
        ):
            self.assertEqual((await self.client.get(self.url)).status_code, 500)
        self.assertEqual(self.stream.closed, 1)

    async def test_openapi_and_invalid_file_id(self) -> None:
        """Контракт описывает binary response без Request body и JSON DTO."""
        operation = self.app.openapi()["paths"][
            "/api/console/files/items/{file_id}/preview/"
        ]["get"]
        self.assertNotIn("requestBody", operation)
        self.assertEqual(
            operation["responses"]["200"]["content"]["application/octet-stream"][
                "schema"
            ],
            {"type": "string", "format": "binary"},
        )
        for status in (401, 403, 404, 409, 415, 503):
            self.assertIn(str(status), operation["responses"])
        self.assertEqual(
            (
                await self.client.get("/api/console/files/items/not-a-uuid/preview/")
            ).status_code,
            422,
        )
        self.repository.content_location.assert_not_awaited()

    async def test_response_closes_on_read_error_early_stop_and_send_failure(
        self,
    ) -> None:
        """Cleanup охватывает EOF, read failure, ранний выход и обрыв до первой порции."""
        for fail in (False, True):
            stream = PreviewTestStream(fail=fail)
            response = GetFilePreviewResponse(
                stream=stream,
                name="file.pdf",
                content_type="application/pdf",
                size_bytes=9,
            )
            if fail:
                with self.assertRaises(StorageUnavailableError):
                    _ = [chunk async for chunk in response.body_iterator]
            else:
                self.assertEqual(await anext(response.body_iterator), b"%PDF-")
                await response.body_iterator.aclose()
            await response.aclose()
            self.assertEqual(stream.closed, 1)
        stream = PreviewTestStream()
        response = GetFilePreviewResponse(
            stream=stream, name="file.pdf", content_type="application/pdf", size_bytes=9
        )

        async def send(_message: dict[str, object]) -> None:
            """Имитирует disconnect при отправке response start."""
            raise OSError("Disconnected")

        with self.assertRaises(ClientDisconnect):
            await response(
                {"type": "http", "asgi": {"spec_version": "2.4"}}, AsyncMock(), send
            )
        self.assertEqual(stream.iterated, 0)
        self.assertEqual(stream.closed, 1)


class PreviewSDKCancellationTests(unittest.IsolatedAsyncioTestCase):
    """Проверяет drain SDK при отменах, используемых ASGI streaming response."""

    async def test_repeated_task_cancel_keeps_sdk_resource_until_thread_finishes(
        self,
    ) -> None:
        """Повторная отмена не освобождает semaphore раньше SDK-потока."""
        await self.check_cancellation(scope_cancel=False)

    async def test_cancelled_anyio_scope_keeps_sdk_resource_until_thread_finishes(
        self,
    ) -> None:
        """ASGI CancelScope не прерывает ожидание синхронной файловой операции."""
        await self.check_cancellation(scope_cancel=True)

    async def test_cancelled_open_and_read_release_the_sdk_connection(self) -> None:
        """Отмена ASGI во время get_object/read не оставляет HTTP response в pool."""
        for opening in (True, False):
            with self.subTest(opening=opening):
                adapter = MinioStorageAdapter(
                    FilesSettings(
                        endpoint="localhost:9000",
                        access_key="test",
                        secret_key="test",
                        secure=False,
                        concurrency=1,
                    )
                )
                tenant, bucket = uuid4(), uuid4()
                location = StorageLocation(
                    tenant, bucket, f"dnk-tenant-{tenant.hex}", "minio", "system_minio"
                )
                response = Mock()
                started, release = threading.Event(), threading.Event()
                scopes: list[CancelScope] = []

                def work(*_arguments: object) -> object:
                    """Задерживает синхронное открытие или чтение response до cancel."""
                    started.set()
                    release.wait(3)
                    return response if opening else b"data"

                adapter._client = Mock()
                adapter._client.get_object.side_effect = work
                response.read.side_effect = work

                async def scoped() -> None:
                    """Прерывает чтение в scope, который используется streaming response."""
                    with CancelScope() as scope:
                        scopes.append(scope)
                        if opening:
                            await adapter.open(location, uuid4().hex)
                        else:
                            stream = MinioFileContentStream(response, adapter)
                            await anext(stream)

                task = asyncio.create_task(scoped())
                try:
                    self.assertTrue(await asyncio.to_thread(started.wait, 1))
                    scopes[0].cancel()
                    await asyncio.sleep(0.01)
                    self.assertFalse(task.done())
                finally:
                    release.set()
                    await task
                response.close.assert_called_once_with()
                response.release_conn.assert_called_once_with()
                self.assertEqual(adapter._limit._value, 1)

    async def check_cancellation(self, *, scope_cancel: bool) -> None:
        """Запускает контролируемый SDK-поток и проверяет обе разновидности отмены."""
        adapter = MinioStorageAdapter(
            FilesSettings(
                endpoint="localhost:9000",
                access_key="test",
                secret_key="test",
                secure=False,
                concurrency=1,
            )
        )
        started, release, finished = (
            threading.Event(),
            threading.Event(),
            threading.Event(),
        )
        scopes: list[CancelScope] = []

        def work() -> None:
            """Удерживает внешний эффект до явного разрешения теста."""
            started.set()
            release.wait(3)
            finished.set()

        async def scoped() -> None:
            """Повторяет отменяемый scope ASGI task group."""
            with CancelScope() as scope:
                scopes.append(scope)
                await adapter.call(work)

        task = asyncio.create_task(scoped() if scope_cancel else adapter.call(work))
        try:
            self.assertTrue(await asyncio.to_thread(started.wait, 1))
            if scope_cancel:
                scopes[0].cancel()
            else:
                task.cancel()
            await asyncio.sleep(0.01)
            if not scope_cancel:
                task.cancel()
                await asyncio.sleep(0.01)
            self.assertFalse(task.done())
            self.assertFalse(finished.is_set())
            self.assertEqual(adapter._limit._value, 0)
        finally:
            release.set()
            await asyncio.gather(task, return_exceptions=True)
        self.assertTrue(finished.is_set())
        self.assertEqual(adapter._limit._value, 1)
