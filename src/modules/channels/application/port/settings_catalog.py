"""Проверка настроек контента по общим справочникам проекта."""

from typing import Protocol


class ChannelSettingsCatalog(Protocol):
    """Проверяет доступность нормализованных кодов, разрешённых пакетом платформы."""

    async def ensure_available(
        self, *, currency: str, locales: tuple[str, ...]
    ) -> None:
        """Отклоняет отсутствующую валюту или неактивный язык до изменения канала."""
        ...
