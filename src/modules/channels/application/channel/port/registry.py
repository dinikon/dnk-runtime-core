from typing import Any
from dataclasses import dataclass
from typing import Protocol
from src.modules.channels.domain.channel.value_object.kind import ChannelKind
from src.modules.channels.domain.channel.value_object.channel_type import ChannelType


@dataclass(frozen=True, slots=True)
class ChannelDefinition:
    """Передаёт определение платформы между реестром и сценариями Application."""

    kind: ChannelKind
    type: ChannelType
    label: str
    can_configure: bool
    unavailable_reason: str | None
    config_version: int
    config: dict[str, Any]

    @property
    def reads_publications(self) -> bool:
        """Возвращает явно заявленную возможность чтения публикаций платформы."""
        return self.config.get("capabilities", {}).get("read_publications") is True


class ChannelRegistryPort(Protocol):
    """Предоставляет актуальные определения платформ без зависимости от их хранения."""

    def get(self, kind: str) -> ChannelDefinition:
        """Возвращает независимый снимок определения либо ошибку отсутствия."""
        ...

    def list_all(self) -> tuple[ChannelDefinition, ...]:
        """Возвращает каталог доступных и пока недоступных платформ."""
        ...
