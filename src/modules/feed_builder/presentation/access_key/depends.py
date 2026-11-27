from typing import Annotated

from fastapi import Depends

from src.modules.feed_builder.application.access_key.command.issue_feed_access_key.handler import (
    IssueFeedAccessKeyHandler,
)
from src.modules.feed_builder.application.access_key.command.revoke_feed_access_key.handler import (
    RevokeFeedAccessKeyHandler,
)
from src.modules.feed_builder.application.access_key.query.list_feed_access_keys.handler import (
    ListFeedAccessKeysHandler,
)
from src.modules.feed_builder.infrastructure.access_key.persistence.query_repository import (
    SqlAlchemyFeedAccessKeyListRepository,
)
from src.modules.feed_builder.infrastructure.access_key.persistence.repository import (
    SqlAlchemyFeedAccessKeyRepository,
)
from src.modules.feed_builder.presentation.feed.depends import FeedSettingsRepositoryDep
from src.modules.shared.presentation.persistence.depends import UoWDep
from src.modules.shared.presentation.time.depends import ClockDep
from src.modules.shared.presentation.uuid.depends import UuidDep


def get_list_access_keys_handler(
    uow: UoWDep, clock: ClockDep
) -> ListFeedAccessKeysHandler:
    """Подключает read-side токенов к текущему tenant."""
    return ListFeedAccessKeysHandler(
        SqlAlchemyFeedAccessKeyListRepository(uow.session), clock
    )


def get_issue_access_key_handler(
    uow: UoWDep,
    feeds: FeedSettingsRepositoryDep,
    clock: ClockDep,
    identifiers: UuidDep,
) -> IssueFeedAccessKeyHandler:
    """Собирает выпуск ключа на общей tenant-сессии."""
    return IssueFeedAccessKeyHandler(
        feeds, SqlAlchemyFeedAccessKeyRepository(uow.session), clock, identifiers
    )


def get_revoke_access_key_handler(
    uow: UoWDep, clock: ClockDep
) -> RevokeFeedAccessKeyHandler:
    """Подключает репозиторий отзыва к внешней транзакции."""
    return RevokeFeedAccessKeyHandler(
        SqlAlchemyFeedAccessKeyRepository(uow.session), clock
    )


ListFeedAccessKeysHandlerDep = Annotated[
    ListFeedAccessKeysHandler, Depends(get_list_access_keys_handler)
]
IssueFeedAccessKeyHandlerDep = Annotated[
    IssueFeedAccessKeyHandler, Depends(get_issue_access_key_handler)
]
RevokeFeedAccessKeyHandlerDep = Annotated[
    RevokeFeedAccessKeyHandler, Depends(get_revoke_access_key_handler)
]
