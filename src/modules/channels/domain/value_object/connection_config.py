"""Изолированный снимок публичных настроек подключения."""

from copy import deepcopy
from dataclasses import dataclass, field

from src.modules.channels.domain.error import InvalidChannelStateError
from src.modules.channels.domain.types import JsonObject


@dataclass(frozen=True, slots=True)
class ConnectionConfigVO:
    """Сохраняет документ независимо от словарей вызывающей стороны."""

    version: int
    endpoint: str
    _settings: JsonObject = field(repr=False)

    def __post_init__(self) -> None:
        """Проверяет форму снимка; правила платформы остаются в её пакете."""
        if (
            type(self.version) is not int
            or self.version < 1
            or not isinstance(self.endpoint, str)
            or not isinstance(self._settings, dict)
        ):
            raise InvalidChannelStateError(
                "Некорректный снимок конфигурации подключения."
            )
        object.__setattr__(self, "_settings", deepcopy(self._settings))

    @classmethod
    def create(
        cls, *, version: int, endpoint: str, settings: JsonObject
    ) -> "ConnectionConfigVO":
        """Создаёт снимок, не сохраняя ссылки на входные настройки."""
        return cls(version=version, endpoint=endpoint, _settings=settings)

    @property
    def settings(self) -> JsonObject:
        """Возвращает независимую копию, включая вложенные списки и словари."""
        return deepcopy(self._settings)
