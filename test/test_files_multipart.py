"""Предел multipart во время приёма и освобождение spool при любом исходе."""

import asyncio
from tempfile import SpooledTemporaryFile
import unittest
from unittest.mock import patch

from fastapi import HTTPException
from starlette.requests import Request
from src.config.infrastructure.files_config import FilesSettings
from src.modules.files.presentation.stored_file.multipart import (
    parse_upload_file_request,
)


class FilesMultipartTests(unittest.IsolatedAsyncioTestCase):
    """Проверяет parser независимо от storage и Content-Length."""

    def body(self, content: bytes, *, ending: bool = True) -> bytes:
        """Создаёт один multipart-файл без необязательных полей."""
        return (
            b'--file-test\r\nContent-Disposition: form-data; name="file"; filename="file.pdf"\r\n\r\n'
            + content
            + (b"\r\n--file-test--\r\n" if ending else b"")
        )

    def request(self, body: bytes, *, cancel: bool = False) -> Request:
        """Возвращает ASGI stream с небольшими порциями и необязательной отменой."""
        chunks = [
            body[start : start + 32 * 1024] for start in range(0, len(body), 32 * 1024)
        ]
        sent = 0

        async def receive() -> dict[str, object]:
            """Передаёт очередную часть без Content-Length."""
            nonlocal sent
            if cancel and sent:
                raise asyncio.CancelledError()
            if sent < len(chunks):
                data = chunks[sent]
                sent += 1
                return {
                    "type": "http.request",
                    "body": data,
                    "more_body": sent < len(chunks) or cancel,
                }
            return {"type": "http.request", "body": b"", "more_body": False}

        return Request(
            {
                "type": "http",
                "method": "POST",
                "path": "/",
                "headers": [
                    (b"content-type", b"multipart/form-data; boundary=file-test")
                ],
            },
            receive,
        )

    async def test_spool_rolls_to_disk_and_closes_after_success_or_handler_error(
        self,
    ) -> None:
        """Большой файл не остаётся целиком в памяти; финализация закрывает handle."""
        content = b"x" * (1024 * 1024 + 17)
        parser = parse_upload_file_request(
            self.request(self.body(content)), len(content)
        )
        payload = await anext(parser)
        self.assertEqual(payload.file.size, len(content))
        self.assertTrue(payload.file.file._rolled)
        self.assertEqual(payload.file.file.read(16), b"x" * 16)
        await parser.aclose()
        self.assertTrue(payload.file.file.closed)
        parser = parse_upload_file_request(self.request(self.body(b"")), 1)
        payload = await anext(parser)
        self.assertEqual(payload.file.size, 0)
        with self.assertRaises(RuntimeError):
            await parser.athrow(RuntimeError("consumer failed"))
        self.assertTrue(payload.file.file.closed)

    async def test_limit_truncation_and_cancellation_close_all_created_sources(
        self,
    ) -> None:
        """Parser освобождает незавершённые файлы на 413/422 и CancelledError."""
        for body, limit, cancel, expected in (
            (self.body(b"x" * 70000), 65000, False, 413),
            (self.body(b"x" * 70000, ending=False), 70000, False, 422),
            (self.body(b"x" * 70000), 70000, True, None),
        ):
            sources = []

            def spool(*args: object, **kwargs: object) -> object:
                """Запоминает реальные handles для проверки закрытия после исключения."""
                source = SpooledTemporaryFile(*args, **kwargs)
                sources.append(source)
                return source

            with patch("starlette.formparsers.SpooledTemporaryFile", side_effect=spool):
                parser = parse_upload_file_request(
                    self.request(body, cancel=cancel), limit
                )
                if expected is None:
                    with self.assertRaises(asyncio.CancelledError):
                        await anext(parser)
                else:
                    with self.assertRaises(HTTPException) as caught:
                        await anext(parser)
                    self.assertEqual(caught.exception.status_code, expected)
            self.assertTrue(sources)
            self.assertTrue(all(source.closed for source in sources))

    async def test_console_limit_is_positive_and_does_not_change_internal_upload(
        self,
    ) -> None:
        """HTTP limit имеет самостоятельный default и не заменяет transfer timeout."""
        self.assertEqual(FilesSettings().console_max_upload_bytes, 104857600)
        self.assertEqual(
            FilesSettings(console_max_upload_bytes=1).operation_timeout_seconds, 600
        )
        from pydantic import ValidationError

        with self.assertRaises(ValidationError):
            FilesSettings(console_max_upload_bytes=0)

    async def test_oversized_headers_and_receive_timeout_are_bounded(self) -> None:
        """Заголовки не растут до file limit; медленный приём прекращается по deadline."""
        from src.config import dnk_config

        header = (
            b"--file-test\r\nX-Large: "
            + b"x" * 70000
            + b'\r\nContent-Disposition: form-data; name="file"; filename="x.pdf"\r\n\r\nx\r\n--file-test--\r\n'
        )
        with self.assertRaises(HTTPException) as caught:
            await anext(parse_upload_file_request(self.request(header), 100000))
        self.assertEqual(caught.exception.status_code, 413)
        request = self.request(self.body(b"x" * 70000))
        original_receive = request._receive
        calls = 0

        async def slow_receive() -> dict[str, object]:
            """Передаёт начало файла, затем ждёт отмены по timeout."""
            nonlocal calls
            calls += 1
            if calls > 1:
                await asyncio.Future()
            return await original_receive()

        request._receive = slow_receive
        with patch.object(dnk_config.FILES, "operation_timeout_seconds", 0.01):
            with self.assertRaises(HTTPException) as caught:
                await anext(parse_upload_file_request(request, 100000))
        self.assertEqual(caught.exception.status_code, 408)
