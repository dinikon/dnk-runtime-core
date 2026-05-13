from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import Any
from uuid import UUID

from src.modules.communication.application.provider_connector.dto import (
    ProviderConnectorDTO,
    ProviderMessageTypeDTO,
)
from src.modules.communication.domain.provider_connector import (
    ProviderConnector,
    ProviderConnectorIdVO,
    ProviderMessageType,
    ProviderMessageTypeIdVO,
)


def provider_connector_entity(row: Mapping[str, Any]) -> ProviderConnector:
    """Мапит runtime row в ProviderConnector."""
    return ProviderConnector(
        provider_connector_id=ProviderConnectorIdVO.from_value(as_uuid(row.get("id"))),
        provider_code=as_str(row.get("provider_code")),
        provider_name=as_str(row.get("provider_name")),
        version=as_str(row.get("version")),
        connector_type=as_str(row.get("connector_type")),
        yaml_spec=as_dict(row.get("yaml_spec")),
        yaml_checksum=as_str(row.get("yaml_checksum")),
        status=as_str(row.get("status")),
        created_at=as_datetime(row.get("created_at")),
        updated_at=as_datetime(row.get("updated_at")),
    )


def provider_connector_dto(row: Mapping[str, Any]) -> ProviderConnectorDTO:
    """Мапит runtime row в ProviderConnectorDTO."""
    spec = as_dict(row.get("yaml_spec"))
    return ProviderConnectorDTO(
        provider_connector_id=as_uuid(row.get("id")),
        provider_code=as_str(row.get("provider_code")),
        provider_name=as_str(row.get("provider_name")),
        version=as_str(row.get("version")),
        connector_type=as_str(row.get("connector_type")),
        channels=as_str_list(spec.get("channels") or []),
        config_schema=as_dict(spec.get("config_schema") or {}),
        secrets_schema=as_dict(spec.get("secrets_schema") or {}),
        status=as_str(row.get("status")),
        created_at=as_datetime(row.get("created_at")),
        updated_at=as_datetime(row.get("updated_at")),
    )


def provider_message_type_entity(row: Mapping[str, Any]) -> ProviderMessageType:
    """Мапит runtime row в ProviderMessageType."""
    return ProviderMessageType(
        provider_message_type_id=ProviderMessageTypeIdVO.from_value(
            as_uuid(row.get("id"))
        ),
        provider_connector_id=ProviderConnectorIdVO.from_value(
            as_uuid(row.get("provider_connector_id"))
        ),
        message_type_code=as_str(row.get("message_type_code")),
        channel_code=as_str(row.get("channel_code")),
        name=as_str(row.get("name")),
        field_schema=as_dict(row.get("field_schema")),
        ui_schema=as_dict(row.get("ui_schema")),
        is_active=as_bool(row.get("is_active")),
    )


def provider_message_type_dto(row: Mapping[str, Any]) -> ProviderMessageTypeDTO:
    """Мапит runtime row в ProviderMessageTypeDTO."""
    return ProviderMessageTypeDTO(
        provider_message_type_id=as_uuid(row.get("id")),
        provider_connector_id=as_uuid(row.get("provider_connector_id")),
        message_type_code=as_str(row.get("message_type_code")),
        channel_code=as_str(row.get("channel_code")),
        name=as_str(row.get("name")),
        field_schema=as_dict(row.get("field_schema")),
        ui_schema=as_dict(row.get("ui_schema")),
        is_active=as_bool(row.get("is_active")),
    )


def as_uuid(value: Any) -> UUID:
    """Достает UUID из runtime row."""
    if isinstance(value, UUID):
        return value
    if isinstance(value, str):
        return UUID(value)
    raise TypeError("Runtime row must contain UUID value.")


def as_datetime(value: Any) -> datetime:
    """Достает datetime из runtime row."""
    if isinstance(value, datetime):
        return value
    raise TypeError("Runtime row must contain datetime value.")


def as_str(value: Any) -> str:
    """Достает строку из runtime row."""
    if isinstance(value, str):
        return value
    raise TypeError("Runtime row must contain string value.")


def as_dict(value: Any) -> dict[str, Any]:
    """Достает dict из runtime row."""
    if isinstance(value, dict):
        return dict(value)
    raise TypeError("Runtime row must contain dict value.")


def as_bool(value: Any) -> bool:
    """Достает bool из runtime row."""
    if isinstance(value, bool):
        return value
    raise TypeError("Runtime row must contain bool value.")


def as_str_list(value: Any) -> list[str]:
    """Достает list[str] из runtime row."""
    if isinstance(value, list) and all(isinstance(item, str) for item in value):
        return list(value)
    raise TypeError("Runtime row must contain list[str] value.")


__all__ = [
    "provider_connector_dto",
    "provider_connector_entity",
    "provider_message_type_dto",
    "provider_message_type_entity",
]
