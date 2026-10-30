from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class DisableRepresentationExportCommand:
    """Параметры сценария disable_representation_export из доверенного HTTP-контекста."""

    tenant_id: UUID
    channel_id: UUID
    group_id: UUID
    actor_id: UUID
    expected_revision: int
    expected_binding_revision: int
    expected_config_revision: int
