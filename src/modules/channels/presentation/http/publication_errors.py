"""Безопасные HTTP-коды сценариев синхронизации и публикаций."""

from fastapi import HTTPException

from src.modules.channels.application.error import ChannelInputError
from src.modules.channels.domain.channel.error import ChannelError
from src.modules.channels.domain.sync_run.error import (
    SyncRunError,
    SyncRunNotFoundError,
    SyncNotAvailableError,
)
from src.modules.channels.domain.external_publication.error import (
    ExternalPublicationError,
    ExternalPublicationNotFoundError,
)
from src.modules.channels.presentation.http.access import channel_http_error


def publication_http_error(
    error: ChannelError | ChannelInputError | SyncRunError | ExternalPublicationError,
) -> HTTPException:
    """Не возвращает текст исключения либо внешний payload."""
    if isinstance(error, (ChannelError, ChannelInputError)):
        return channel_http_error(error)
    if isinstance(error, SyncRunNotFoundError):
        return HTTPException(404, detail={"code": "sync_run_not_found"})
    if isinstance(error, ExternalPublicationNotFoundError):
        return HTTPException(404, detail={"code": "publication_not_found"})
    if isinstance(error, SyncNotAvailableError):
        return HTTPException(409, detail={"code": "sync_not_available"})
    return HTTPException(422, detail={"code": "publication_state_invalid"})
