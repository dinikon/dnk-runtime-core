from uuid import UUID
from pydantic import BaseModel


class SetPublicationExportResponse(BaseModel):
    """Возвращает версии изменённых представлений."""

    revisions: dict[UUID, int]
