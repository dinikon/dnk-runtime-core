from uuid import UUID
from pydantic import BaseModel


class UpdateContentBlockResponse(BaseModel):
    """Ответ HTTP-сценария update_content_block."""

    id: UUID
    revision: int
