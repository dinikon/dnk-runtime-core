from collections.abc import Awaitable, Callable

from fastapi import Request, Response
from fastapi.responses import JSONResponse

from src.modules.channels.application.error import ChannelInputError
from src.modules.channels.domain.channel.error import ChannelError
from src.modules.channels.domain.product_representation.error import (
    ProductRepresentationError,
)
from src.modules.channels.presentation.catalog_binding.http.route import BindingRoute
from src.modules.channels.presentation.http.access import channel_http_error


class RepresentationRoute(BindingRoute):
    """Добавляет безопасные ошибки представлений к общим границам Channels."""

    def get_route_handler(self) -> Callable[[Request], Awaitable[Response]]:
        """Перехватывает только ожидаемые отказы без включения исходного ввода."""
        handler = super().get_route_handler()

        async def handle(request: Request) -> Response:
            """Сохраняет rollback внешнего UoW до преобразования ошибки в HTTP."""
            try:
                return await handler(request)
            except ProductRepresentationError as error:
                return JSONResponse(
                    status_code=409 if error.conflict else 422,
                    content={"detail": {"code": error.code}},
                )
            except (ChannelError, ChannelInputError) as error:
                response = channel_http_error(error)
                return JSONResponse(
                    status_code=response.status_code,
                    content={"detail": response.detail},
                )

        return handle
