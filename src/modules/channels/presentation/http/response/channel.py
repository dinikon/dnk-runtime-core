from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict


class ChannelResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    name: str
    kind: str
    type: str
    config_version: int
    connection_settings: dict[str, str]
    configured_secret_fields: list[str]
    is_active: bool
    status: str
    created_at: datetime
    updated_at: datetime
    created_by: UUID
    updated_by: UUID


class ChannelKindResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    kind: str
    type: str
    label: str
    can_configure: bool
    unavailable_reason: str | None


class ChannelConfigResponse(ChannelKindResponse):
    config_version: int
    config: dict
