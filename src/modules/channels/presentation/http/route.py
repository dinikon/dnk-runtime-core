from fastapi.routing import APIRoute
from fastapi.exceptions import RequestValidationError
from fastapi import HTTPException
from src.modules.channels.domain.error import (
    ChannelNotFoundError,
    ChannelConfigConflictError,
    ChannelSecretsUnavailableError,
    ChannelValidationError,
    InvalidChannelError,
)


class ChannelRoute(APIRoute):
    """Единая транспортная граница: ошибки никогда не отражают credentials."""

    def get_route_handler(self):
        original = super().get_route_handler()

        async def handle(request):
            try:
                return await original(request)
            except RequestValidationError as exc:
                raise HTTPException(
                    status_code=422,
                    detail=[
                        {
                            "loc": list(e["loc"]),
                            "msg": "Некорректное значение поля.",
                            "type": e["type"],
                        }
                        for e in exc.errors()
                    ],
                ) from None
            except ChannelValidationError as exc:
                raise HTTPException(status_code=422, detail=list(exc.errors)) from None
            except (
                ChannelNotFoundError,
                ChannelConfigConflictError,
                ChannelSecretsUnavailableError,
                InvalidChannelError,
            ) as exc:
                status = (
                    404
                    if isinstance(exc, ChannelNotFoundError)
                    else (
                        409
                        if isinstance(exc, ChannelConfigConflictError)
                        else (
                            503
                            if isinstance(exc, ChannelSecretsUnavailableError)
                            else 422
                        )
                    )
                )
                raise HTTPException(status_code=status, detail=str(exc)) from None

        return handle
