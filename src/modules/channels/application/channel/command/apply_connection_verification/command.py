from dataclasses import dataclass
from uuid import UUID
from src.modules.channels.application.plugin_contract import VerifyConnectionOutcomeDTO


@dataclass(frozen=True, slots=True)
class ApplyConnectionVerificationCommand:
    """Описывает один шаг apply_connection_verification, без session и HTTP Request."""

    tenant_id: UUID
    actor_id: UUID
    channel_id: UUID
    generation: int
    job_id: UUID
    outcome: VerifyConnectionOutcomeDTO
