from src.modules.reference_data.application.port.catalog import CatalogRepositoryPort


class ReferenceLocaleReaderAdapter:
    """Переход к Application-контракту глобального справочника локалей."""

    def __init__(self, repository: CatalogRepositoryPort) -> None:
        self._repository = repository

    async def is_active(self, code: str) -> bool:
        return await self._repository.has_active_locale(code)
