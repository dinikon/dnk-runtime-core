from collections.abc import AsyncIterator
from typing import Annotated
from fastapi import Depends, HTTPException, Request
from pydantic import ValidationError
from starlette.formparsers import MultiPartParser, MultiPartException
from starlette.datastructures import Headers
from python_multipart.exceptions import MultipartParseError
from src.config import dnk_config
from src.modules.catalog.presentation.catalog_import.http.request.create_catalog_import import (
    CreateCatalogImportRequest,
)


class ImportMultipartParser(MultiPartParser):
    """Ограничивает фактический поток до помещения bytes в spool."""

    def __init__(
        self, headers: Headers, stream: AsyncIterator[bytes], limit: int
    ) -> None:
        """Разрешает один файл и три коротких поля мастера."""
        super().__init__(headers, stream, max_files=1, max_fields=3, max_part_size=8192)
        self.limit, self.received, self.header_size = limit, 0, 0
        self.completed = False

    def on_part_begin(self) -> None:
        """Сбрасывает предел заголовков очередной части."""
        super().on_part_begin()
        self.header_size = 0

    def on_header_field(self, data: bytes, start: int, end: int) -> None:
        """Не допускает неограниченных multipart-заголовков."""
        self.header_size += end - start
        if self.header_size > 65536:
            raise MultiPartException("Multipart headers exceeded.")
        super().on_header_field(data, start, end)

    def on_header_value(self, data: bytes, start: int, end: int) -> None:
        """Ограничивает также значения заголовков."""
        self.header_size += end - start
        if self.header_size > 65536:
            raise MultiPartException("Multipart headers exceeded.")
        super().on_header_value(data, start, end)

    def on_part_data(self, data: bytes, start: int, end: int) -> None:
        """Проверяет размер файла независимо от Content-Length."""
        if self._current_part.file is not None:
            self.received += end - start
            if self.received > self.limit:
                raise HTTPException(413, "Файл превышает лимит импорта.")
        super().on_part_data(data, start, end)

    def on_end(self) -> None:
        """Не принимает оборванный multipart как полный файл."""
        self.completed = True


async def parse_import_source(
    request: Request,
) -> AsyncIterator[CreateCatalogImportRequest]:
    """Читает JSON-ссылку или ограниченный multipart и закрывает все spool."""
    parser: ImportMultipartParser | None = None
    try:
        kind = request.headers.get("content-type", "").split(";", 1)[0].strip()
        if kind == "application/json":
            body = bytearray()
            async for chunk in request.stream():
                body.extend(chunk)
                if len(body) > 16384:
                    raise HTTPException(413, "Слишком большой запрос источника.")
            payload = CreateCatalogImportRequest.model_validate_json(body)
        elif kind == "multipart/form-data":

            async def bounded() -> AsyncIterator[bytes]:
                """Ограничивает суммарный запрос и размер порций парсера."""
                size = 0
                async for chunk in request.stream():
                    size += len(chunk)
                    if size > dnk_config.CATALOG_IMPORT.source_max_bytes + 65536:
                        raise HTTPException(413, "Файл превышает лимит импорта.")
                    for offset in range(0, len(chunk), 65536):
                        yield chunk[offset : offset + 65536]

            parser = ImportMultipartParser(
                request.headers, bounded(), dnk_config.CATALOG_IMPORT.source_max_bytes
            )
            form = await parser.parse()
            if not parser.completed or len(form.multi_items()) != len(form):
                raise HTTPException(422, "Некорректный multipart.")
            payload = CreateCatalogImportRequest.model_validate(dict(form))
        else:
            raise HTTPException(422, "Укажите JSON-ссылку или multipart-файл.")
        if (payload.file is None) == (payload.url is None) or (
            payload.file and payload.file.size == 0
        ):
            raise HTTPException(
                422, "Укажите ровно один непустой источник: файл или ссылку."
            )
        yield payload
    except (ValidationError, MultiPartException, MultipartParseError) as error:
        raise HTTPException(422, "Некорректный источник импорта.") from error
    finally:
        if parser:
            for file in parser._files_to_close_on_error:
                file.close()


ImportSourceDep = Annotated[CreateCatalogImportRequest, Depends(parse_import_source)]
