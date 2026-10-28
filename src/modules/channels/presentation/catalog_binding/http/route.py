from collections.abc import Callable, Awaitable
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError
from src.modules.channels.presentation.http.safe_route import ChannelsRoute
from src.modules.channels.domain.catalog_binding.error import CatalogBindingError
from src.modules.catalog.domain.error import CatalogError


class BindingRoute(ChannelsRoute):
    """Преобразует безопасные ошибки сценариев и commit общей транзакции."""

    def get_route_handler(self) -> Callable[[Request], Awaitable[Response]]:
        """Не раскрывает SQL, значения payload и технические исключения владельцев."""
        handler = super().get_route_handler()

        async def handle(request: Request) -> Response:
            """Сохраняет контракт авторизации и перехватывает ожидаемые отказы."""
            try:
                return await handler(request)
            except CatalogBindingError as error:
                status = (
                    404
                    if error.code.endswith(("_not_found", "_missing"))
                    else 409 if error.conflict else 422
                )
                return JSONResponse(
                    status_code=status, content={"detail": {"code": error.code}}
                )
            except CatalogError:
                return JSONResponse(
                    status_code=422,
                    content={"detail": {"code": "binding_catalog_invalid"}},
                )
            except IntegrityError:
                return JSONResponse(
                    status_code=409,
                    content={"detail": {"code": "binding_publication_occupied"}},
                )

        return handle
