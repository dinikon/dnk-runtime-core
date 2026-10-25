from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class MaintainCatalogImportsResultDTO:
    """Результат отдельного сценария maintain_catalog_imports."""

    expired: int
    failed: int
    deleted: int
