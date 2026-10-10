from uuid import UUID
from pydantic import BaseModel


class ReplaceVariantsResponse(BaseModel):
    """Подтверждённый HTTP-результат сценария replace_variants."""

    id: UUID
    revision: int
