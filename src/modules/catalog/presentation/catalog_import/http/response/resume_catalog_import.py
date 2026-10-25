from uuid import UUID
from pydantic import BaseModel


class ResumeCatalogImportResponse(BaseModel):
    """Состояние продолженного импорта без сброса его результатов."""

    id: UUID
    status: str
    generation: int
