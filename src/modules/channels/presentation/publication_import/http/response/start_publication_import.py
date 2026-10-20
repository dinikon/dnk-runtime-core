from uuid import UUID
from pydantic import BaseModel


class StartPublicationImportResponse(BaseModel):
    """Возвращает адрес конкретной подготовки после действия."""

    preparation_id: UUID
