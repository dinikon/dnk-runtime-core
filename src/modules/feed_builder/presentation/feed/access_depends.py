from typing import Annotated

from fastapi import Depends

from src.modules.feed_builder.application.feed.command.change_feed_access_mode.handler import (
    ChangeFeedAccessModeHandler,
)
from src.modules.feed_builder.presentation.feed.depends import FeedSettingsRepositoryDep
from src.modules.shared.presentation.time.depends import ClockDep


def get_change_feed_access_mode_handler(
    feeds: FeedSettingsRepositoryDep, clock: ClockDep
) -> ChangeFeedAccessModeHandler:
    """Подключает команду смены режима к существующему репозиторию настроек."""
    return ChangeFeedAccessModeHandler(feeds, clock)


ChangeFeedAccessModeHandlerDep = Annotated[
    ChangeFeedAccessModeHandler, Depends(get_change_feed_access_mode_handler)
]
