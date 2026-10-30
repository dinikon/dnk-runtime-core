from collections.abc import Awaitable, Callable

from fastapi import Request, Response
from fastapi.responses import JSONResponse

from src.modules.channels.application.content_feed.error import FeedBuildError
from src.modules.channels.domain.content_feed.error import ContentFeedError
from src.modules.channels.presentation.content_media.http.route import ContentMediaRoute


class ContentFeedRoute(ContentMediaRoute):
    """Преобразует безопасные причины после отката UoW, не отдавая обрывок XML."""

    def get_route_handler(self) -> Callable[[Request], Awaitable[Response]]:
        """Обрабатывает ошибки обоих интерфейсов: Console и публичного endpoint."""
        handler = super().get_route_handler()

        async def handle(request: Request) -> Response:
            """Не включает исходный URL, токен или XML в сообщение об ошибке."""
            try:
                response = await handler(request)
                response.headers["Cache-Control"] = "no-store"
                response.headers["Referrer-Policy"] = "no-referrer"
                return response
            except ContentFeedError as error:
                status = (
                    404
                    if error.code in {"feed_not_found", "feed_channel_not_found"}
                    else 409 if error.conflict else 422
                )
                return JSONResponse(
                    status_code=status,
                    content={"detail": {"code": error.code}},
                    headers={"Cache-Control": "no-store"},
                )
            except FeedBuildError as error:
                status = (
                    503
                    if error.unavailable
                    else (
                        403
                        if error.code in {"feed_access_denied", "feed_file_forbidden"}
                        else 422
                    )
                )
                return JSONResponse(
                    status_code=status,
                    content={
                        "detail": {
                            "code": error.code,
                            "publication_id": (
                                str(error.publication_id)
                                if error.publication_id
                                else None
                            ),
                            "field": error.field,
                        }
                    },
                    headers={"Cache-Control": "no-store"},
                )

        return handle
