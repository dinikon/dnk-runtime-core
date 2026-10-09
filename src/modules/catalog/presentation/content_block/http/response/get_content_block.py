from uuid import UUID
from pydantic import BaseModel


class GetContentBlockResponse(BaseModel):
    """Ответ HTTP-сценария get_content_block."""

    id: UUID
    code: str
    is_system: bool
    revision: int
    label: str | None
    locales: tuple[str, ...]
    value_type: str
