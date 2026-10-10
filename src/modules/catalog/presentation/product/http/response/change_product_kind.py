from uuid import UUID
from pydantic import BaseModel


class ChangeProductKindResponse(BaseModel):
    """Подтверждённый HTTP-результат сценария change_product_kind."""

    id: UUID
    revision: int
