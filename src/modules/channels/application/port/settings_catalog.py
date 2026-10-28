"""Проверка используемых каналом кодов через владельца справочников."""

from typing import Protocol


class ChannelSettingsCatalog(Protocol):
    """Не раскрывает Channels способ хранения reference_data."""

    async def ensure_available(
        self, *, currency: str, locales: tuple[str, ...]
    ) -> None:
        """Отклоняет отсутствующий либо неактивный код."""
        ...
