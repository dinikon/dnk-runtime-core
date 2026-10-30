from dataclasses import dataclass
from uuid import UUID
from src.modules.channels.domain.product_representation.overrides import (
    RepresentationOverridesVO,
)


@dataclass(frozen=True, slots=True)
class SaveRepresentationCommand:
    """Параметры сценария save_representation из доверенного HTTP-контекста."""

    tenant_id: UUID
    channel_id: UUID
    group_id: UUID
    actor_id: UUID
    expected_revision: int
    expected_binding_revision: int
    expected_config_revision: int
    overrides: RepresentationOverridesVO
