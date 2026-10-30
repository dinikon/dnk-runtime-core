from collections.abc import Awaitable, Callable
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from src.modules.channels.domain.content_delivery.error import ContentDeliveryError
from src.modules.channels.presentation.content_media.http.route import ContentMediaRoute


class ContentDeliveryRoute(ContentMediaRoute):
    """Преобразует ожидаемые ошибки после rollback общего UoW."""

    def get_route_handler(self) -> Callable[[Request], Awaitable[Response]]:
        """Не включает запрос или внутреннее исключение в ответ."""
        handler = super().get_route_handler()

        async def handle(request: Request) -> Response:
            """Сохраняет безопасные статусы сценариев доставки."""
            try:
                return await handler(request)
            except ContentDeliveryError as error:
                status = (
                    404
                    if error.code == "content_delivery_not_found"
                    else (
                        403
                        if error.code
                        in {"content_access_denied", "content_file_forbidden"}
                        else 409 if error.conflict else 422
                    )
                )
                return JSONResponse(
                    status_code=status,
                    content={"detail": {"code": error.code}},
                    headers={"Cache-Control": "no-store"},
                )

        return handle
