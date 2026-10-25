import csv
import io
from collections.abc import Iterator
from tempfile import SpooledTemporaryFile
from uuid import UUID
from fastapi.responses import StreamingResponse
from starlette.background import BackgroundTask
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.catalog.presentation.catalog_import.depends import (
    ListCatalogImportRowsHandlerDep,
    import_http_error,
)
from src.modules.catalog.application.catalog_import.query.list_catalog_import_rows.query import (
    ListCatalogImportRowsQuery,
)
from src.modules.catalog.domain.error import CatalogError


def report_cell(value: str) -> str:
    """Не позволяет таблицам выполнять содержимое отчёта как формулу."""
    return (
        "'" + value
        if value.lstrip().startswith(("=", "+", "-", "@"))
        or value.startswith(("\t", "\r", "\n"))
        else value
    )


async def export_catalog_import_report(
    import_id: UUID,
    context: AuthenticatedRequestContextDep,
    handler: ListCatalogImportRowsHandlerDep,
) -> StreamingResponse:
    """Строит CSV порциями в spool до закрытия request UoW."""
    spool = SpooledTemporaryFile(max_size=1024 * 1024)
    wrapper = io.TextIOWrapper(spool, encoding="utf-8-sig", newline="")
    try:
        writer = csv.writer(wrapper)
        writer.writerow(
            ["Номер", "SKU", "Результат", "ID товара", "Ошибки", "Предупреждения"]
        )
        offset = 0
        while True:
            page = await handler.execute(
                ListCatalogImportRowsQuery(import_id, None, offset, 1000)
            )
            for row in page.items:
                writer.writerow(
                    [
                        row.number,
                        report_cell(row.sku or ""),
                        row.outcome,
                        str(row.item_id or ""),
                        report_cell("; ".join(row.errors)),
                        report_cell("; ".join(row.warnings)),
                    ]
                )
            offset += len(page.items)
            if offset >= page.total or not page.items:
                break
        wrapper.flush()
        wrapper.detach()
        spool.seek(0)
    except BaseException as error:
        wrapper.close()
        if isinstance(error, CatalogError):
            raise import_http_error(error) from error
        raise

    def content() -> Iterator[bytes]:
        """Освобождает spool также при прерывании ответа клиентом."""
        try:
            while chunk := spool.read(65536):
                yield chunk
        finally:
            spool.close()

    return StreamingResponse(
        content(),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="catalog-import-{import_id}.csv"'
        },
        background=BackgroundTask(spool.close),
    )
