from typing import Protocol
from src.modules.channels.application.port.registry import ChannelDefinition


class ConnectionValidatorPort(Protocol):
    def validate(self, definition: ChannelDefinition, settings: dict) -> None: ...
