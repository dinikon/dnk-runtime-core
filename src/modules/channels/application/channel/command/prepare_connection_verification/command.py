from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class PrepareConnectionVerificationCommand:
    """Описывает один шаг prepare_connection_verification, без session и HTTP Request."""

    tenant_id: UUID
    actor_id: UUID
    channel_id: UUID
    generation: int
    job_id: UUID
