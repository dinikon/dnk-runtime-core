from dataclasses import dataclass
from datetime import datetime

from src.modules.channels.domain.channel.error import InvalidChannelStateError


@dataclass(frozen=True, slots=True)
class StockSyncSettingsVO:
    """Разрешение отправки и поколение политики одного подключения."""

    allow_export: bool
    revision: int
    changed_at: datetime

    def __post_init__(self) -> None:
        """Отклоняет некорректные значения без неявного преобразования типов."""
        if (
            type(self.allow_export) is not bool
            or type(self.revision) is not int
            or self.revision < 1
            or not isinstance(self.changed_at, datetime)
            or self.changed_at.tzinfo is None
        ):
            raise InvalidChannelStateError(
                "Некорректные настройки синхронизации остатков."
            )
