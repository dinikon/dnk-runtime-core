from fastapi import HTTPException
from src.modules.channels.domain.error import (
    ChannelsError,
    ChannelsDraftValidationError,
    ChannelsNotFoundError,
    ChannelsConflictError,
    ChannelsUnavailableError,
)


def http_error(error: ChannelsError) -> HTTPException:
    """Переводит безопасные предметные коды в HTTP без SQL и payload."""
    if isinstance(error, ChannelsDraftValidationError):
        return HTTPException(
            422,
            {
                "code": "invalid_catalog_draft",
                "issues": [
                    {"field": field, "message": message}
                    for field, message in error.issues
                ],
            },
        )
    status = (
        404
        if isinstance(error, ChannelsNotFoundError)
        else (
            409
            if isinstance(error, ChannelsConflictError)
            else 503 if isinstance(error, ChannelsUnavailableError) else 422
        )
    )
    return HTTPException(status, str(error))
