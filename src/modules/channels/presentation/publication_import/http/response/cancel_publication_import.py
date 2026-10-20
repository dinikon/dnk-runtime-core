from uuid import UUID
from pydantic import BaseModel


class CancelPublicationImportResponse(BaseModel):
    """Возвращает адрес конкретной подготовки после действия."""

    preparation_id: UUID
    revision: int
