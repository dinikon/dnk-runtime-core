from collections.abc import Awaitable, Callable
from fastapi import Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute


class ChannelsRoute(APIRoute):
    """Удаляет input/ctx из HTTP-ошибок валидации секретосодержащих запросов."""

    def get_route_handler(self) -> Callable[[Request], Awaitable[Response]]:
        """Оборачивает только маршруты Channels, сохраняя поведение соседних API."""
        handler = super().get_route_handler()

        async def safe(request: Request) -> Response:
            """Не возвращает тело запроса даже при синтаксически некорректном JSON."""
            try:
                return await handler(request)
            except RequestValidationError:
                return JSONResponse(
                    status_code=422,
                    content={
                        "detail": {
                            "code": "request_invalid",
                            "message": "Проверьте обязательные поля и формат запроса.",
                        }
                    },
                )

        return safe
