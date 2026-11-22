from uuid import UUID

from fastapi import HTTPException

from src.modules.feed_builder.domain.error import FeedBuilderDomainError
from src.modules.feed_builder.domain.feed.error import (
    FeedArchivedError,
    FeedNotFoundError,
    FeedVersionConflictError,
)
from src.modules.feed_builder.domain.publication.error import (
    InvalidPublicationOverrideError,
    PublicationNotFoundError,
    PublicationTransitionError,
    PublicationVersionConflictError,
)


def override_http_error(error: FeedBuilderDomainError, field_id: UUID) -> HTTPException:
    """Преобразует доменную ошибку редактирования в адресованный ответ."""
    if isinstance(error, (FeedNotFoundError, PublicationNotFoundError)):
        return HTTPException(
            404, {"code": "PUBLICATION_RESOURCE_NOT_FOUND", "message": str(error)}
        )
    if isinstance(
        error,
        (
            FeedArchivedError,
            FeedVersionConflictError,
            PublicationTransitionError,
            PublicationVersionConflictError,
        ),
    ):
        return HTTPException(
            409, {"code": "PUBLICATION_CONFLICT", "message": str(error)}
        )
    return HTTPException(
        422,
        {
            "code": (
                error.code
                if isinstance(error, InvalidPublicationOverrideError)
                else "PUBLICATION_INVALID"
            ),
            "message": str(error),
            "field_id": str(field_id),
            "path": error.path,
        },
    )
