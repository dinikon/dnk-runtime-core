from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import Any
from uuid import UUID

from src.modules.communication.application.provider_connection.dto import (
    ProviderConnectionDTO,
)
from src.modules.communication.domain.provider_connection import (
    ProviderConnectionEntity,
    ProviderConnectionIdVO,
    ProviderConnectionNameVO,
    ProviderConnectionStatusVO,
)
from src.modules.communication.domain.provider_connector import (
    ProviderConnector,
    ProviderConnectorIdVO,
)
from src.modules.shared import EntityIdVO


def provider_connection_entity(
    *,
    tenant_id: EntityIdVO,
    row: Mapping[str, Any],
) -> ProviderConnectionEntity:
    """Мапит runtime row в ProviderConnectionEntity."""
    return ProviderConnectionEntity(
        provider_connection_id=ProviderConnectionIdVO.from_value(
            as_uuid(row.get("id"))
        ),
        created_at=as_datetime(row.get("created_at")),
        updated_at=as_datetime(row.get("updated_at")),
        tenant_id=tenant_id,
        provider_connector_id=ProviderConnectorIdVO.from_value(
            as_uuid(row.get("provider_connector_id"))
        ),
        connection_name=ProviderConnectionNameVO(as_str(row.get("connection_name"))),
        channel_code=as_str(row.get("channel_code")),
        config=as_dict(row.get("config")),
        secret_ref=as_optional_str(row.get("secret_ref")),
        secrets_b64=as_optional_str(row.get("secrets_b64")),
        status=ProviderConnectionStatusVO(as_str(row.get("status"))),
    )


def provider_connection_dto(
    *,
    tenant_id: EntityIdVO,
    row: Mapping[str, Any],
) -> ProviderConnectionDTO:
    """Мапит runtime row в ProviderConnectionDTO."""
    return ProviderConnectionDTO(
        provider_connection_id=as_uuid(row.get("id")),
        tenant_id=tenant_id.uuid,
        provider_connector_id=as_uuid(row.get("provider_connector_id")),
        connection_name=as_str(row.get("connection_name")),
        channel_code=as_str(row.get("channel_code")),
        config=as_dict(row.get("config")),
        secret_ref=as_optional_str(row.get("secret_ref")),
        has_secrets=bool(as_optional_str(row.get("secrets_b64"))),
        status=as_str(row.get("status")),
        created_at=as_datetime(row.get("created_at")),
        updated_at=as_datetime(row.get("updated_at")),
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


def as_optional_str(value: Any) -> str | None:
    """Достает optional строку из runtime row."""
    if value is None:
        return None
    return as_str(value)


def as_dict(value: Any) -> dict[str, Any]:
    """Достает dict из runtime row."""
    if isinstance(value, dict):
        return dict(value)
    raise TypeError("Runtime row must contain dict value.")


__all__ = [
    "provider_connection_dto",
    "provider_connection_entity",
    "provider_connector_entity",
]
