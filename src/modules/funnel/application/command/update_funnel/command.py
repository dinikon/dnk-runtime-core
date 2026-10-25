from dataclasses import dataclass
from uuid import UUID
from src.modules.funnel.application.values import StageInput


@dataclass(frozen=True, slots=True)
class UpdateFunnelCommand:
    """Вход сценария update определения процесса."""

    tenant_id: UUID
    actor_id: UUID
    funnel_id: UUID
    expected_revision: int
    name: str
    stages: tuple[StageInput, ...]
