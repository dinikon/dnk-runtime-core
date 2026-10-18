from collections.abc import Awaitable, Callable
from fastapi import Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute


class ChannelsRoute(APIRoute):
    """Не раскрывает input/ctx секретного body в validation response."""

    def get_route_handler(self) -> Callable[[Request], Awaitable[Response]]:
        """Сохраняет стандартный FastAPI handler с безопасной обработкой ошибок ввода."""
        original = super().get_route_handler()

        async def route(request: Request) -> Response:
            """Исключает исходные значения credentials и поля exception context."""
            try:
                return await original(request)
            except RequestValidationError as error:
                return JSONResponse(
                    status_code=422,
                    content={
                        "detail": [
                            {
                                "loc": item["loc"],
                                "type": item["type"],
                                "msg": item["msg"],
                            }
                            for item in error.errors()
                        ]
                    },
                )

        return route
