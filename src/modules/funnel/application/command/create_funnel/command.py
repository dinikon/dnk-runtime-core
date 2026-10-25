from dataclasses import dataclass
from uuid import UUID
from src.modules.funnel.application.values import StageInput


@dataclass(frozen=True, slots=True)
class CreateFunnelCommand:
    """Вход сценария create определения процесса."""

    tenant_id: UUID
    actor_id: UUID
    model_key: str
    name: str
    stages: tuple[StageInput, ...]
