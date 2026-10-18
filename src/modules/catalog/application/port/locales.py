from typing import Protocol


class LocalePort(Protocol):
    """Проверка активности локалей через публичные контракты reference_data."""

    async def ensure_active(self, code: str) -> None:
        """Отклоняет запись в неизвестную либо неактивную locale."""
        ...
