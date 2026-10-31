from pydantic import BaseModel, ConfigDict, Field

from src.modules.channels.domain.types import JsonObject
from src.modules.channels.presentation.http.request.config import (
    ConnectionConfigRequest,
)


class CreateChannelRequest(BaseModel):
    """Полная атомарная форма создания канала и подключения."""

    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)
    name: str = Field(min_length=1, max_length=255)
    platform_kind: str = Field(min_length=1, max_length=64)
    config: ConnectionConfigRequest
    credentials: JsonObject = Field(repr=False)
