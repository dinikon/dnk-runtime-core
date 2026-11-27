from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class IssueFeedAccessKeyResponse(BaseModel):
    """Передаёт новый секрет только при выпуске."""

    model_config = ConfigDict(from_attributes=True)
    id: UUID
    name: str
    created_at: datetime
    expires_at: datetime | None
    token: str = Field(repr=False)
