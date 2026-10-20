from src.modules.channels.domain.external_publication.value_object.core import JsonValue
from uuid import UUID
from pydantic import BaseModel


class GetConnectionResponse(BaseModel):
    """Определяет отдельный HTTP-ответ сценария get_connection."""

    channel_id: UUID
    connection_id: UUID
    revision: int
    endpoint: str
    settings: dict[str, JsonValue]
    resource_identity: str | None
    verification_status: str
    verification_job_id: UUID | None
    generation: int
    is_paused: bool
    credentials_present: bool
    candidate_present: bool
    reason_code: str | None
    scope_limitations: tuple[str, ...]
