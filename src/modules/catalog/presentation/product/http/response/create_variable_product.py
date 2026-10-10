from uuid import UUID
from pydantic import BaseModel


class CreateVariableProductResponse(BaseModel):
    """Подтверждённый HTTP-результат сценария create_variable_product."""

    id: UUID
    revision: int
