from uuid import UUID
from pydantic import BaseModel


class StartPublicationInitializationResponse(BaseModel):
    """Определяет отдельный HTTP-ответ сценария start_publication_initialization."""

    run_id: UUID
    status: str
    job_id: UUID | None
