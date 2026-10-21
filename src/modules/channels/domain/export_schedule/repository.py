from typing import Protocol
from uuid import UUID
from src.modules.channels.domain.export_schedule.aggregate import ExportSchedule


class ExportScheduleRepository(Protocol):
    """Сохраняет policy после блокировки владельца Channel."""

    async def get(self, channel_id: UUID) -> ExportSchedule:
        """Возвращает явный manual default при отсутствии policy."""
        ...

    async def save(self, schedule: ExportSchedule) -> None:
        """Сохраняет настройки в общей транзакции с durable intent."""
        ...
