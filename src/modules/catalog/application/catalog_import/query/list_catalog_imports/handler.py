from src.modules.catalog.application.catalog_import.read_port import ImportReadPort
from .query import ListCatalogImportsQuery
from .dto import ListCatalogImportsResultDTO


class ListCatalogImportsHandler:
    """Читает конкретную проекцию list_catalog_imports."""

    def __init__(self, repository: ImportReadPort) -> None:
        """Получает порт чтения текущего tenant."""
        self.repository = repository

    async def execute(
        self, query: ListCatalogImportsQuery
    ) -> ListCatalogImportsResultDTO:
        """Возвращает типизированную проекцию без записи данных."""
        return await self.repository.list(query.offset, query.limit)
