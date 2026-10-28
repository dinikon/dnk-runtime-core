from uuid import UUID
from pydantic import BaseModel, ConfigDict


class PairRequest(BaseModel):
    """Не принимает чужие поля или неявные преобразования связей."""

    model_config = ConfigDict(extra="forbid")
    catalog_position_id: UUID
    publication_id: UUID
