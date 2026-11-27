from uuid import UUID

from fastapi import Request
from starlette.responses import Response

from src.modules.feed_builder.domain.feed.enum.export_format import ExportFormat
from src.modules.feed_builder.presentation.export_state.depends import (
    DownloadPublicFeedHandlerDep,
    PublicFeedStreamsDep,
)
from src.modules.feed_builder.presentation.export_state.http.download import (
    serve_active_feed,
)
from src.modules.shared.presentation.http.depends import RequestHostDep


async def download_public_feed_xml(
    public_link_id: UUID,
    request: Request,
    host: RequestHostDep,
    handler: DownloadPublicFeedHandlerDep,
    streams: PublicFeedStreamsDep,
) -> Response:
    """Выдаёт активный XML после проверки доступа."""
    return await serve_active_feed(
        request, public_link_id, host, ExportFormat.XML, handler, streams
    )
