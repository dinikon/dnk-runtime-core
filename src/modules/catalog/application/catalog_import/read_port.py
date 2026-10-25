from typing import Protocol
from uuid import UUID
from src.modules.catalog.application.catalog_import.query.get_catalog_import.dto import (
    GetCatalogImportResultDTO,
)
from src.modules.catalog.application.catalog_import.query.list_catalog_imports.dto import (
    ListCatalogImportsResultDTO,
)
from src.modules.catalog.application.catalog_import.query.list_catalog_import_rows.dto import (
    ListCatalogImportRowsResultDTO,
)


class ImportReadPort(Protocol):
    """Читает готовые проекции без восстановления агрегата."""

    async def get(self, identifier: UUID) -> GetCatalogImportResultDTO:
        """Возвращает состояние и ограниченный предпросмотр."""
        ...

    async def list(self, offset: int, limit: int) -> ListCatalogImportsResultDTO:
        """Возвращает страницу запусков."""
        ...

    async def rows(
        self, identifier: UUID, outcome: str | None, offset: int, limit: int
    ) -> ListCatalogImportRowsResultDTO:
        """Возвращает страницу результатов одного запуска."""
        ...
