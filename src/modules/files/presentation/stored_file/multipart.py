import asyncio
from collections.abc import AsyncIterator
from typing import Annotated
from fastapi import Depends, HTTPException, Request
from pydantic import ValidationError
from python_multipart.exceptions import MultipartParseError
from starlette.datastructures import Headers
from starlette.formparsers import MultiPartException, MultiPartParser
from src.config import dnk_config
from src.modules.files.presentation.stored_file.http.request.upload_file import (
    UploadFileRequest,
)

MULTIPART_OVERHEAD_BYTES = 64 * 1024


class UploadLimitExceeded(MultiPartException):
    """Сигнал превышения лимита во время приёма, до записи части в spool."""


class LimitedFileMultipartParser(MultiPartParser):
    """Принимает один файл, ограничивая его размер независимо от Content-Length."""

    def __init__(
        self, headers: Headers, stream: AsyncIterator[bytes], limit: int
    ) -> None:
        """Ограничивает поля/файлы и сохраняет per-file счётчик приёма."""
        super().__init__(headers, stream, max_files=1, max_fields=1, max_part_size=1024)
        self._limit = limit
        self._file_bytes = 0
        self._header_bytes = 0
        self.completed = False

    def on_part_begin(self) -> None:
        """Сбрасывает счётчик перед новой multipart-частью."""
        super().on_part_begin()
        self._file_bytes = 0
        self._header_bytes = 0

    def _accept_header(self, size: int) -> None:
        """Ограничивает память заголовков части независимо от размера файла."""
        self._header_bytes += size
        if self._header_bytes > MULTIPART_OVERHEAD_BYTES:
            raise UploadLimitExceeded("Console multipart headers exceeded.")

    def on_header_field(self, data: bytes, start: int, end: int) -> None:
        """Ограничивает имя заголовка до накопления parser buffer."""
        self._accept_header(end - start)
        super().on_header_field(data, start, end)

    def on_header_value(self, data: bytes, start: int, end: int) -> None:
        """Ограничивает значение заголовка до накопления parser buffer."""
        self._accept_header(end - start)
        super().on_header_value(data, start, end)

    def on_part_data(self, data: bytes, start: int, end: int) -> None:
        """Отклоняет превышение до добавления bytes в очередь записи spool."""
        if self._current_part.file is not None:
            self._file_bytes += end - start
            if self._file_bytes > self._limit:
                raise UploadLimitExceeded("Console upload limit exceeded.")
        super().on_part_data(data, start, end)

    def on_end(self) -> None:
        """Подтверждает наличие конечной границы multipart, исключая обрыв тела."""
        self.completed = True

    def close_files(self) -> None:
        """Закрывает все созданные spool handles, включая незавершённые части."""
        for source in self._files_to_close_on_error:
            source.close()


def get_console_upload_limit() -> int:
    """Читает Instance limit во внешнем слое, сохраняя consumer upload независимым."""
    return dnk_config.FILES.console_max_upload_bytes


async def bounded_multipart_stream(
    request: Request, limit: int
) -> AsyncIterator[bytes]:
    """Ограничивает полный запрос и порции parser, включая multipart overhead."""
    received = 0
    async for chunk in request.stream():
        received += len(chunk)
        if received > limit + MULTIPART_OVERHEAD_BYTES:
            raise UploadLimitExceeded("Console multipart limit exceeded.")
        for offset in range(0, len(chunk), 64 * 1024):
            yield chunk[offset : offset + 64 * 1024]


async def parse_upload_file_request(
    request: Request, limit: Annotated[int, Depends(get_console_upload_limit)]
) -> AsyncIterator[UploadFileRequest]:
    """Принимает ограниченный multipart и закрывает spool при любом завершении запроса."""
    if (
        request.headers.get("content-type", "").partition(";")[0].strip().lower()
        != "multipart/form-data"
    ):
        raise HTTPException(422, "Multipart file is required.")
    parser = LimitedFileMultipartParser(
        request.headers, bounded_multipart_stream(request, limit), limit
    )
    try:
        try:
            async with asyncio.timeout(dnk_config.FILES.operation_timeout_seconds):
                form = await parser.parse()
            if not parser.completed or len(form.multi_items()) != len(form):
                raise HTTPException(422, "Invalid multipart fields.")
            payload = UploadFileRequest.model_validate(dict(form))
        except UploadLimitExceeded as error:
            raise HTTPException(413, "Console upload limit exceeded.") from error
        except TimeoutError as error:
            raise HTTPException(408, "Console upload reception timed out.") from error
        except (
            MultiPartException,
            MultipartParseError,
            ValidationError,
            LookupError,
        ) as error:
            raise HTTPException(422, "Invalid multipart fields.") from error
        yield payload
    finally:
        parser.close_files()


UploadFileRequestDep = Annotated[
    UploadFileRequest, Depends(parse_upload_file_request, scope="function")
]
