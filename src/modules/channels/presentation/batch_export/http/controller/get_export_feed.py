from collections.abc import AsyncIterator
from uuid import UUID
from fastapi import HTTPException
from src.modules.channels.presentation.batch_export.http.response.get_export_feed import (
    ExportFeedResponse,
)
from src.modules.channels.presentation.batch_export.feed.depends import (
    ExportFeedContextDep,
)
from src.modules.channels.application.batch_export.query.get_export_feed.query import (
    GetExportFeedQuery,
)
from src.modules.channels.application.batch_export.query.get_export_feed.handler import (
    GetExportFeedHandler,
)
from src.modules.channels.infrastructure.batch_export.persistence.queries import (
    SqlAlchemyBatchExportQueries,
)
from src.modules.files.infrastructure.assembly import (
    build_artifact_files_facade,
    get_storage_resolver,
)
from src.modules.files.domain.error import FilesError
from src.modules.channels.domain.error import ChannelsError
from src.modules.shared.infrastructure.persistence.unit_of_work.sqlalchemy import (
    UnitOfWork,
)
from src.modules.shared.infrastructure.time.utc_clock import UtcClock


async def get_export_feed(
    run_id: UUID, context: ExportFeedContextDep
) -> ExportFeedResponse:
    """Отдаёт готовый файл без авторизации Console, сохраняя tenant admission и приватность остальных данных."""
    try:
        async with UnitOfWork(context.sessions) as uow:
            result = await GetExportFeedHandler(
                SqlAlchemyBatchExportQueries(uow.session),
                build_artifact_files_facade(uow.session),
                UtcClock(),
            ).execute(GetExportFeedQuery(context.tenant_id, run_id))
        location = result.location
        stream = (
            await get_storage_resolver()
            .resolve(location.location)
            .open(location.location, location.key)
        )
        context.streams.push_async_callback(stream.aclose)
    except (ChannelsError, FilesError):
        raise HTTPException(404, "export_feed_not_found") from None

    async def chunks() -> AsyncIterator[bytes]:
        """Закрывает объект при завершении, отмене или разрыве соединения клиента."""
        try:
            async for chunk in stream:
                yield chunk
        finally:
            await stream.aclose()

    return ExportFeedResponse(
        chunks(),
        media_type="application/xml",
        headers={
            "Content-Length": str(location.size_bytes),
            "ETag": '"' + result.digest + '"',
            "Cache-Control": "private, no-store",
            "X-Content-Type-Options": "nosniff",
            "Referrer-Policy": "no-referrer",
            "X-Robots-Tag": "noindex, nofollow",
            "Content-Disposition": 'inline; filename="catalog-texts.xml"',
        },
    )
