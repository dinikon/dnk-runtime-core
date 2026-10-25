from src.modules.catalog.application.catalog_import.read_port import ImportReadPort
from .query import GetCatalogImportQuery
from .dto import GetCatalogImportResultDTO


class GetCatalogImportHandler:
    """Читает конкретную проекцию get_catalog_import."""

    def __init__(self, repository: ImportReadPort) -> None:
        """Получает порт чтения текущего tenant."""
        self.repository = repository

    async def execute(self, query: GetCatalogImportQuery) -> GetCatalogImportResultDTO:
        """Возвращает типизированную проекцию без записи данных."""
        return await self.repository.get(query.import_id)
