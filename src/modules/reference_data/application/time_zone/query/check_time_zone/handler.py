from src.modules.reference_data.application.port.catalog import CatalogRepositoryPort
from src.modules.reference_data.application.time_zone.query.check_time_zone.dto import (
    CheckTimeZoneResultDTO,
)
from src.modules.reference_data.application.time_zone.query.check_time_zone.query import (
    CheckTimeZoneQuery,
)


class CheckTimeZoneHandler:
    """Проверяет один код через абстрактный порт общего справочника."""

    def __init__(self, repository: CatalogRepositoryPort) -> None:
        """Принимает repository внешнего UoW без SQLAlchemy-зависимости."""
        self._repository = repository

    async def execute(self, query: CheckTimeZoneQuery) -> CheckTimeZoneResultDTO:
        """Возвращает DTO активности кода без загрузки всего справочника."""
        return CheckTimeZoneResultDTO(
            code=query.code,
            is_active=await self._repository.has_active_time_zone(query.code),
        )
