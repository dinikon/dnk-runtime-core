from dataclasses import dataclass
from typing import Protocol
from src.modules.channels.domain.value_object.kind import ChannelKind
from src.modules.channels.domain.value_object.channel_type import ChannelType


@dataclass(frozen=True, slots=True)
class ChannelDefinition:
    kind: ChannelKind
    type: ChannelType
    label: str
    can_configure: bool
    unavailable_reason: str | None
    config_version: int
    config: dict


class ChannelRegistryPort(Protocol):
    def get(self, kind: str) -> ChannelDefinition: ...
    def list_all(self) -> tuple[ChannelDefinition, ...]: ...
