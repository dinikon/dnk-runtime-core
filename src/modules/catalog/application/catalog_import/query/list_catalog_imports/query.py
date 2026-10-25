from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ListCatalogImportsQuery:
    """Вход отдельного сценария list_catalog_imports."""

    offset: int = 0
    limit: int = 20
