from collections.abc import Awaitable, Callable

from fastapi import Request, Response
from fastapi.responses import JSONResponse

from src.modules.channels.presentation.http.safe_route import ChannelsRoute
from src.modules.channels.domain.stock_sync.error import StockSyncError
from src.modules.channels.domain.channel.error import ChannelError
from src.modules.channels.presentation.http.access import channel_http_error


class StockRoute(ChannelsRoute):
    """Сохраняет безопасный код ожидаемого отказа после rollback UoW."""

    def get_route_handler(self) -> Callable[[Request], Awaitable[Response]]:
        """Не скрывает непредвиденные ошибки и не раскрывает provider payload."""
        handler = super().get_route_handler()

        async def handle(request: Request) -> Response:
            """Преобразует только известные бизнес-отказы."""
            try:
                return await handler(request)
            except StockSyncError as error:
                status = (
                    404
                    if error.code.endswith("_not_found")
                    else 403 if error.code == "stock_export_forbidden" else 422
                )
                return JSONResponse(
                    status_code=status, content={"detail": {"code": error.code}}
                )
            except ChannelError as error:
                http = channel_http_error(error)
                return JSONResponse(
                    status_code=http.status_code, content={"detail": http.detail}
                )

        return handle
