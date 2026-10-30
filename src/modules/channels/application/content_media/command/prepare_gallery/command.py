from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class PrepareGalleryCommand:
    """Конкретное намерение prepare_gallery из доверенного контекста."""

    tenant_id: UUID
    channel_id: UUID
    group_id: UUID
    expected_revision: int
    expected_binding_revision: int
    expected_config_revision: int
