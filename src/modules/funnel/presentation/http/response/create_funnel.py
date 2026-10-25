from uuid import UUID
from pydantic import BaseModel


class CreateFunnelResponse(BaseModel):
    """Отдельный ответ записи процесса."""

    id: UUID
    revision: int
    stage_id_map: dict[str, UUID]
