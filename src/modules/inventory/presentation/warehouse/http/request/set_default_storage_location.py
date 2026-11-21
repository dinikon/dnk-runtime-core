from uuid import UUID

from pydantic import BaseModel, ConfigDict


class SetDefaultStorageLocationRequest(BaseModel):
    """Требует UUID выбранной локации без null и посторонних полей."""

    model_config = ConfigDict(extra="forbid")
    location_id: UUID
