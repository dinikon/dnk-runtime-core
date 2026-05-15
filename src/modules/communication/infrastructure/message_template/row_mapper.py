from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import Any
from uuid import UUID

from src.modules.communication.application.message_template.dto import (
    MessageTemplateDTO,
)
from src.modules.communication.domain.message_template import (
    ChannelCodeVO,
    MessageClassVO,
    MessageTemplateCodeVO,
    MessageTemplateEntity,
    MessageTemplateIdVO,
    MessageTemplateNameVO,
    TemplateStatusVO,
    TemplateVersionEntity,
    TemplateVersionIdVO,
    TemplateVersionStatusVO,
    TemplateVersionTimestampVO,
)
from src.modules.communication.domain.provider_connector import (
    ProviderConnector,
    ProviderConnectorIdVO,
    ProviderMessageType,
    ProviderMessageTypeIdVO,
)
from src.modules.shared import EntityIdVO


def message_template_entity(
    *,
    tenant_id: EntityIdVO,
    row: Mapping[str, Any],
) -> MessageTemplateEntity:
    """Мапит runtime row в MessageTemplateEntity."""
    return MessageTemplateEntity(
        template_id=MessageTemplateIdVO.from_value(as_uuid(row.get("id"))),
        created_at=as_datetime(row.get("created_at")),
        updated_at=as_datetime(row.get("updated_at")),
        tenant_id=tenant_id,
        template_code=MessageTemplateCodeVO(as_str(row.get("template_code"))),
        name=MessageTemplateNameVO(as_str(row.get("name"))),
        description=as_optional_str(row.get("description")),
        provider_connector_id=ProviderConnectorIdVO.from_value(
            as_uuid(row.get("provider_connector_id"))
        ),
        provider_message_type_id=ProviderMessageTypeIdVO.from_value(
            as_uuid(row.get("provider_message_type_id"))
        ),
        channel_code=ChannelCodeVO(as_str(row.get("channel_code"))),
        message_class=MessageClassVO(as_str(row.get("message_class"))),
        status=TemplateStatusVO(as_str(row.get("status"))),
    )


def template_version_entity(row: Mapping[str, Any]) -> TemplateVersionEntity:
    """Мапит runtime row в TemplateVersionEntity."""
    version = row.get("version") or row.get("created_at")
    return TemplateVersionEntity(
        template_version_id=TemplateVersionIdVO.from_value(as_uuid(row.get("id"))),
        created_at=as_datetime(row.get("created_at")),
        activated_at=as_optional_datetime(row.get("activated_at")),
        template_id=MessageTemplateIdVO.from_value(as_uuid(row.get("template_id"))),
        version=TemplateVersionTimestampVO(as_datetime(version)),
        template_payload=as_dict(row.get("template_payload")),
        variables_schema=as_dict(row.get("variables_schema")),
        status=TemplateVersionStatusVO(as_str(row.get("status"))),
    )


def message_template_dto(
    *,
    tenant_id: EntityIdVO,
    row: Mapping[str, Any],
    active_version: Mapping[str, Any] | None,
) -> MessageTemplateDTO:
    """Мапит runtime row в MessageTemplateDTO."""
    return MessageTemplateDTO(
        template_id=as_uuid(row.get("id")),
        tenant_id=tenant_id.uuid,
        template_code=as_str(row.get("template_code")),
        name=as_str(row.get("name")),
        description=as_optional_str(row.get("description")),
        provider_connector_id=as_uuid(row.get("provider_connector_id")),
        provider_message_type_id=as_uuid(row.get("provider_message_type_id")),
        channel_code=as_str(row.get("channel_code")),
        message_class=as_str(row.get("message_class")),
        status=as_str(row.get("status")),
        created_at=as_datetime(row.get("created_at")),
        updated_at=as_datetime(row.get("updated_at")),
        active_version_id=(
            None if active_version is None else as_uuid(active_version.get("id"))
        ),
        active_version=(
            None
            if active_version is None
            else TemplateVersionTimestampVO(
                as_datetime(
                    active_version.get("version") or active_version.get("created_at")
                )
            ).value
        ),
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
        is_active=bool(row.get("is_active")),
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


def as_optional_datetime(value: Any) -> datetime | None:
    """Достает optional datetime из runtime row."""
    if value is None:
        return None
    return as_datetime(value)


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
    "as_uuid",
    "message_template_dto",
    "message_template_entity",
    "provider_connector_entity",
    "provider_message_type_entity",
    "template_version_entity",
]
