from typing import Any
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ChannelKindConfigDTO:
    """Передаёт версию и конфигурацию формы выбранной платформы."""

    kind: str
    type: str
    label: str
    can_configure: bool
    unavailable_reason: str | None
    config_version: int
    config: dict[str, Any]
