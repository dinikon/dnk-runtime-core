from src.modules.reference_data.application.locale.query.list_locales.query import (
    ListLocalesQuery,
)
from src.modules.reference_data.application.port.catalog import CatalogRepositoryPort
from src.modules.reference_data.domain.locale.record import Locale


class ListLocalesHandler:
    """Возвращает список локалей для отображения в интерфейсе."""

    def __init__(self, repository: CatalogRepositoryPort) -> None:
        """Принимает порт чтения глобального справочника."""
        self._repository = repository

    async def execute(self, query: ListLocalesQuery) -> list[Locale]:
        """Временно ограничивает выдачу тремя языками для демо."""
        records = await self._repository.list_locales()
        # TODO: После демо удалить фильтр и вернуть records целиком.
        return [record for record in records if record.code in {"uk", "ru", "en"}]
