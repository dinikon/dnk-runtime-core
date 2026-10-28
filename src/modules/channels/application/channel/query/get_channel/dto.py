from dataclasses import dataclass

from src.modules.channels.application.channel.port.query_repository import (
    ChannelReadRow,
)


@dataclass(frozen=True, slots=True)
class GetChannelDTO:
    """Результат сценария чтения GetChannel."""

    channel: ChannelReadRow
