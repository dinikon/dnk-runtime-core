from src.modules.reference_data.application.port.catalog import CatalogRepositoryPort
from src.modules.catalog.domain.error import InvalidCatalogValueError


class ReferenceDataLocales:
    """Адаптирует публичный Application-контракт reference_data к порту Catalog."""

    def __init__(self, reference: CatalogRepositoryPort) -> None:
        """Принимает контракт справочника без импорта его SQL-моделей."""
        self._reference = reference

    async def ensure_active(self, code: str) -> None:
        """Проверяет точный активный код; не назначает язык tenant."""
        if not await self._reference.has_active_locale(code):
            raise InvalidCatalogValueError("Locale отсутствует или неактивна.")
