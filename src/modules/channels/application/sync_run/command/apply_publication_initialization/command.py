from dataclasses import dataclass
from uuid import UUID
from src.modules.channels.application.plugin_contract import (
    ReadPublicationPageOutcomeDTO,
)


@dataclass(frozen=True, slots=True)
class ApplyPublicationInitializationCommand:
    """Описывает один шаг apply_publication_initialization, без session и HTTP Request."""

    tenant_id: UUID
    actor_id: UUID
    run_id: UUID
    sequence: int
    outcome: ReadPublicationPageOutcomeDTO | None
    error_code: str | None = None
    retryable: bool = False
