from dataclasses import dataclass, field
from uuid import UUID
from src.modules.channels.domain.publication_import.value_object.snapshot import (
    ImportSnapshotVO,
)


@dataclass(frozen=True, slots=True)
class ApplyPublicationImportStepCommand:
    """Фиксирует сетевой результат только текущего шага подготовки."""

    tenant_id: UUID
    preparation_id: UUID
    sequence: int
    snapshot: ImportSnapshotVO | None = None
    image_id: str | None = None
    image_data: bytes | None = field(default=None, repr=False)
    image_content_type: str | None = None
    error_code: str | None = None
