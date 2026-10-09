from src.modules.reference_data.application.time_zone.query.check_time_zone.handler import (
    CheckTimeZoneHandler,
)
from src.modules.reference_data.application.time_zone.query.check_time_zone.query import (
    CheckTimeZoneQuery,
)


class ReferenceDataTimeZoneReader:
    """Адаптирует публичный Application-контракт Reference Data к порту Warehousing."""

    def __init__(self, handler: CheckTimeZoneHandler) -> None:
        """Принимает внешний reader на session общего UoW, без новой транзакции."""
        self._handler = handler

    async def is_active(self, code: str) -> bool:
        """Возвращает только признак активности, без передачи чужих моделей."""
        result = await self._handler.execute(CheckTimeZoneQuery(code=code))
        return result.is_active
