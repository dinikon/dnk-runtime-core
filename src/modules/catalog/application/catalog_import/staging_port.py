from typing import Protocol
from uuid import UUID
from src.modules.catalog.application.catalog_import.read_models import ImportAnalysisDTO


class ImportAnalysisPort(Protocol):
    """Сохраняет подготовленный снимок предпросмотра в транзакции публикации."""

    async def describe(self, identifier: UUID, analysis: ImportAnalysisDTO) -> None:
        """Записывает ограниченные метаданные и образцы без изменения жизненного цикла."""
        ...
