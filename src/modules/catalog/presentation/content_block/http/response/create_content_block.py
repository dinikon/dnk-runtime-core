from uuid import UUID
from pydantic import BaseModel


class CreateContentBlockResponse(BaseModel):
    """Ответ HTTP-сценария create_content_block."""

    id: UUID
    revision: int
