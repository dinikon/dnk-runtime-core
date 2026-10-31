from dataclasses import dataclass

from src.modules.channels.application.port.query_repository import (
    ChannelReadRow,
)


@dataclass(frozen=True, slots=True)
class ListChannelsDTO:
    """Результат сценария чтения ListChannels."""

    items: tuple[ChannelReadRow, ...]
    total: int
    offset: int
    limit: int
