from fastapi import HTTPException

from src.modules.feed_builder.domain.error import FeedBuilderDomainError
from src.modules.feed_builder.domain.feed.error import (
    FeedArchivedError,
    FeedNotFoundError,
    FeedVersionConflictError,
)


def export_http_error(error: FeedBuilderDomainError) -> HTTPException:
    """Сопоставляет ошибки сценария с контрактом Console."""
    if isinstance(error, FeedNotFoundError):
        return HTTPException(404, {"code": "FEED_NOT_FOUND", "message": str(error)})
    if isinstance(error, (FeedVersionConflictError, FeedArchivedError)):
        return HTTPException(409, {"code": "FEED_CONFLICT", "message": str(error)})
    return HTTPException(422, {"code": "EXPORT_INVALID", "message": str(error)})
