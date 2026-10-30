from collections.abc import Awaitable, Callable
from fastapi import Request, Response
from fastapi.responses import JSONResponse

from src.modules.channels.domain.content_media.error import ContentMediaError
from src.modules.shared.application.crypto.error import (
    CipherNotConfigured,
    CiphertextUnreadable,
)
from src.modules.channels.presentation.product_representation.http.route import (
    RepresentationRoute,
)
from src.modules.files.application.port.storage import (
    StorageConfigurationError,
    StorageOwnershipError,
    StorageUnavailableError,
)


class ContentMediaRoute(RepresentationRoute):
    """Сохраняет безопасные причины отказа без URL или SDK response."""

    def get_route_handler(self) -> Callable[[Request], Awaitable[Response]]:
        """Обрабатывает исключения после rollback внешнего UoW."""
        handler = super().get_route_handler()

        async def handle(request: Request) -> Response:
            """Не различает отсутствующий ресурс, чужой tenant и недоступный файл."""
            try:
                return await handler(request)
            except ContentMediaError as error:
                status = (
                    404
                    if error.code in ("media_not_found", "media_file_unavailable")
                    else (
                        403
                        if error.code == "media_file_forbidden"
                        else 409 if error.conflict else 422
                    )
                )
                return JSONResponse(
                    status_code=status,
                    content={
                        "detail": {
                            "code": "media_not_found" if status == 404 else error.code
                        }
                    },
                    headers={"Cache-Control": "no-store"},
                )
            except StorageOwnershipError:
                return JSONResponse(
                    status_code=404,
                    content={"detail": {"code": "media_not_found"}},
                    headers={"Cache-Control": "no-store"},
                )
            except (StorageUnavailableError, StorageConfigurationError):
                return JSONResponse(
                    status_code=503,
                    content={"detail": {"code": "media_storage_unavailable"}},
                    headers={"Cache-Control": "no-store"},
                )
            except CipherNotConfigured:
                return JSONResponse(
                    status_code=503,
                    content={"detail": {"code": "channels_not_configured"}},
                )
            except CiphertextUnreadable:
                return JSONResponse(
                    status_code=422,
                    content={"detail": {"code": "media_access_unreadable"}},
                )

        return handle
