from dataclasses import dataclass
from typing import Any
from uuid import UUID


@dataclass(frozen=True, slots=True)
class ProviderMessageTypeDTO:
    """DTO provider message type для application boundary."""

    provider_message_type_id: UUID
    provider_connector_id: UUID
    message_type_code: str
    channel_code: str
    name: str
    field_schema: dict[str, Any]
    ui_schema: dict[str, Any]
    is_active: bool


__all__ = ["ProviderMessageTypeDTO"]
