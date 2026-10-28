"""Название канала как самостоятельное значение."""

from dataclasses import dataclass

from src.modules.channels.domain.channel.error import InvalidChannelNameError


@dataclass(frozen=True, slots=True)
class ChannelNameVO:
    """Нормализует название и проверяет его собственные ограничения."""

    value: str

    def __post_init__(self) -> None:
        """Обрезает пробелы и отклоняет пустое либо слишком длинное имя."""
        if not isinstance(self.value, str) or not 1 <= len(self.value.strip()) <= 255:
            raise InvalidChannelNameError("Некорректное название канала.")
        object.__setattr__(self, "value", self.value.strip())
