from dataclasses import dataclass

from src.modules.channels.application.port.query_repository import (
    ChannelReadRow,
)


@dataclass(frozen=True, slots=True)
class GetChannelDTO:
    """Результат сценария чтения GetChannel."""

    channel: ChannelReadRow
