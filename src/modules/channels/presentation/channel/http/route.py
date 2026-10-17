from collections.abc import Awaitable, Callable

from fastapi import HTTPException, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.routing import APIRoute


class ChannelRoute(APIRoute):
    """Удаляет входные значения из ошибок транспортной валидации credentials."""

    def get_route_handler(self) -> Callable[[Request], Awaitable[Response]]:
        """Оборачивает только валидацию FastAPI; ошибки сценариев переводят контроллеры."""
        original = super().get_route_handler()

        async def handle(request: Request) -> Response:
            """Передаёт безопасную ошибку исключением, сохраняя rollback внешнего UoW."""
            try:
                return await original(request)
            except RequestValidationError as exc:
                raise HTTPException(
                    status_code=422,
                    detail=[
                        {
                            "loc": list(error["loc"]),
                            "msg": "Некорректное значение поля.",
                            "type": error["type"],
                        }
                        for error in exc.errors()
                    ],
                ) from None

        return handle
