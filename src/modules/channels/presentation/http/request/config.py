from pydantic import BaseModel, ConfigDict, Field

from src.modules.channels.domain.types import JsonObject
from src.modules.channels.domain.value_object.connection_config import (
    ConnectionConfigVO,
)


class ConnectionConfigRequest(BaseModel):
    """Публичная конфигурация для выбора платформенного codec."""

    model_config = ConfigDict(extra="forbid")
    version: int = Field(ge=1)
    endpoint: str = Field(max_length=2048)
    settings: JsonObject

    def to_value(self) -> ConnectionConfigVO:
        """Преобразует HTTP-модель в обычное значение приложения."""
        return ConnectionConfigVO.create(
            version=self.version, endpoint=self.endpoint, settings=self.settings
        )
