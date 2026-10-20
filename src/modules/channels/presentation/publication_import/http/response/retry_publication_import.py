from uuid import UUID
from pydantic import BaseModel


class RetryPublicationImportResponse(BaseModel):
    """Возвращает адрес конкретной подготовки после действия."""

    preparation_id: UUID
    revision: int
