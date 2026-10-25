from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class MaintainCatalogImportsCommand:
    """Вход отдельного сценария maintain_catalog_imports."""

    import_id: UUID
    now: datetime
