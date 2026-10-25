from src.modules.catalog.application.catalog_import.read_port import ImportReadPort
from .query import ListCatalogImportRowsQuery
from .dto import ListCatalogImportRowsResultDTO


class ListCatalogImportRowsHandler:
    """Читает конкретную проекцию list_catalog_import_rows."""

    def __init__(self, repository: ImportReadPort) -> None:
        """Получает порт чтения текущего tenant."""
        self.repository = repository

    async def execute(
        self, query: ListCatalogImportRowsQuery
    ) -> ListCatalogImportRowsResultDTO:
        """Возвращает типизированную проекцию без записи данных."""
        return await self.repository.rows(
            query.import_id, query.outcome, query.offset, query.limit
        )
