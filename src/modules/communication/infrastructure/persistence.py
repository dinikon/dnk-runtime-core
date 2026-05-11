from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

import sqlalchemy as sa
import uuid6
from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from src.modules.shared.db import Base, PortableJSON, StringUUID


class ProviderConnectorDefinitionModel(Base):
    """SQLAlchemy model for provider connector YAML definitions."""

    __tablename__ = "communication_provider_connector_definition"
    __table_args__ = (
        UniqueConstraint(
            "provider_code",
            "version",
            name="uq_provider_connector_version",
        ),
    )

    provider_connector_id: Mapped[UUID] = mapped_column(
        StringUUID,
        primary_key=True,
        default=uuid6.uuid7,
        nullable=False,
    )
    provider_code: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    provider_name: Mapped[str] = mapped_column(String(255), nullable=False)
    version: Mapped[str] = mapped_column(String(64), nullable=False)
    connector_type: Mapped[str] = mapped_column(String(64), nullable=False)
    yaml_spec: Mapped[dict[str, Any]] = mapped_column(PortableJSON, nullable=False)
    yaml_checksum: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        server_default=sa.text("'ACTIVE'"),
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.current_timestamp(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
        nullable=False,
    )


class ProviderConnectionModel(Base):
    """SQLAlchemy model for tenant-specific provider connections."""

    __tablename__ = "communication_provider_connection"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "connection_code",
            name="uq_provider_connection_code",
        ),
    )

    provider_connection_id: Mapped[UUID] = mapped_column(
        StringUUID,
        primary_key=True,
        default=uuid6.uuid7,
        nullable=False,
    )
    tenant_id: Mapped[UUID] = mapped_column(StringUUID, nullable=False, index=True)
    provider_connector_id: Mapped[UUID] = mapped_column(
        StringUUID,
        ForeignKey("communication_provider_connector_definition.provider_connector_id"),
        nullable=False,
        index=True,
    )
    connection_code: Mapped[str] = mapped_column(String(255), nullable=False)
    connection_name: Mapped[str] = mapped_column(String(255), nullable=False)
    channel_code: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    config: Mapped[dict[str, Any]] = mapped_column(
        PortableJSON,
        nullable=False,
        default=dict,
    )
    secret_ref: Mapped[str | None] = mapped_column(Text, nullable=True)
    secrets_b64: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        server_default=sa.text("'ACTIVE'"),
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.current_timestamp(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
        nullable=False,
    )


class ProviderMessageTypeModel(Base):
    """SQLAlchemy model for provider-specific message type schemas."""

    __tablename__ = "communication_provider_message_type"
    __table_args__ = (
        UniqueConstraint(
            "provider_connector_id",
            "message_type_code",
            name="uq_provider_message_type",
        ),
    )

    provider_message_type_id: Mapped[UUID] = mapped_column(
        StringUUID,
        primary_key=True,
        default=uuid6.uuid7,
        nullable=False,
    )
    provider_connector_id: Mapped[UUID] = mapped_column(
        StringUUID,
        ForeignKey("communication_provider_connector_definition.provider_connector_id"),
        nullable=False,
        index=True,
    )
    message_type_code: Mapped[str] = mapped_column(String(255), nullable=False)
    channel_code: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    field_schema: Mapped[dict[str, Any]] = mapped_column(PortableJSON, nullable=False)
    ui_schema: Mapped[dict[str, Any]] = mapped_column(
        PortableJSON,
        nullable=False,
        default=dict,
    )
    is_active: Mapped[bool] = mapped_column(
        sa.Boolean,
        nullable=False,
        default=True,
        server_default=sa.text("true"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.current_timestamp(),
        nullable=False,
    )


class MessageTemplateModel(Base):
    """SQLAlchemy model for tenant message templates."""

    __tablename__ = "communication_message_template"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "template_code",
            name="uq_message_template_code",
        ),
    )

    template_id: Mapped[UUID] = mapped_column(
        StringUUID,
        primary_key=True,
        default=uuid6.uuid7,
        nullable=False,
    )
    tenant_id: Mapped[UUID] = mapped_column(StringUUID, nullable=False, index=True)
    template_code: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    provider_connector_id: Mapped[UUID] = mapped_column(
        StringUUID,
        ForeignKey("communication_provider_connector_definition.provider_connector_id"),
        nullable=False,
        index=True,
    )
    provider_message_type_id: Mapped[UUID] = mapped_column(
        StringUUID,
        ForeignKey("communication_provider_message_type.provider_message_type_id"),
        nullable=False,
        index=True,
    )
    channel_code: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    message_class: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    status: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        server_default=sa.text("'DRAFT'"),
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.current_timestamp(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
        nullable=False,
    )


class TemplateVersionModel(Base):
    """SQLAlchemy model for versioned template payloads."""

    __tablename__ = "communication_template_version"
    __table_args__ = (
        UniqueConstraint(
            "template_id",
            "version_no",
            name="uq_template_version",
        ),
    )

    template_version_id: Mapped[UUID] = mapped_column(
        StringUUID,
        primary_key=True,
        default=uuid6.uuid7,
        nullable=False,
    )
    template_id: Mapped[UUID] = mapped_column(
        StringUUID,
        ForeignKey("communication_message_template.template_id"),
        nullable=False,
        index=True,
    )
    version_no: Mapped[int] = mapped_column(Integer, nullable=False)
    template_payload: Mapped[dict[str, Any]] = mapped_column(
        PortableJSON, nullable=False
    )
    variables_schema: Mapped[dict[str, Any]] = mapped_column(
        PortableJSON,
        nullable=False,
        default=dict,
    )
    status: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        server_default=sa.text("'DRAFT'"),
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.current_timestamp(),
        nullable=False,
    )
    activated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )


class CommunicationRequestModel(Base):
    """SQLAlchemy model for inbound communication send commands."""

    __tablename__ = "communication_request"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "idempotency_key",
            name="uq_communication_idempotency",
        ),
    )

    communication_request_id: Mapped[UUID] = mapped_column(
        StringUUID,
        primary_key=True,
        default=uuid6.uuid7,
        nullable=False,
    )
    tenant_id: Mapped[UUID] = mapped_column(StringUUID, nullable=False, index=True)
    initiator_type: Mapped[str] = mapped_column(String(64), nullable=False)
    initiator_ref_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    correlation_id: Mapped[UUID | None] = mapped_column(StringUUID, nullable=True)
    idempotency_key: Mapped[str | None] = mapped_column(String(255), nullable=True)
    message_class: Mapped[str] = mapped_column(String(64), nullable=False)
    channel_code: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    template_id: Mapped[UUID] = mapped_column(
        StringUUID,
        ForeignKey("communication_message_template.template_id"),
        nullable=False,
    )
    template_version_id: Mapped[UUID] = mapped_column(
        StringUUID,
        ForeignKey("communication_template_version.template_version_id"),
        nullable=False,
    )
    contact_id: Mapped[UUID | None] = mapped_column(StringUUID, nullable=True)
    recipient_address: Mapped[str] = mapped_column(Text, nullable=False)
    recipient_snapshot: Mapped[dict[str, Any]] = mapped_column(
        PortableJSON,
        nullable=False,
        default=dict,
    )
    variables: Mapped[dict[str, Any]] = mapped_column(
        PortableJSON,
        nullable=False,
        default=dict,
    )
    scheduled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    status: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        server_default=sa.text("'ACCEPTED'"),
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.current_timestamp(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
        nullable=False,
    )


class OutboundMessageModel(Base):
    """SQLAlchemy model for concrete outbound messages."""

    __tablename__ = "communication_outbound_message"

    outbound_message_id: Mapped[UUID] = mapped_column(
        StringUUID,
        primary_key=True,
        default=uuid6.uuid7,
        nullable=False,
    )
    tenant_id: Mapped[UUID] = mapped_column(StringUUID, nullable=False, index=True)
    communication_request_id: Mapped[UUID] = mapped_column(
        StringUUID,
        ForeignKey("communication_request.communication_request_id"),
        nullable=False,
        index=True,
    )
    provider_connection_id: Mapped[UUID] = mapped_column(
        StringUUID,
        ForeignKey("communication_provider_connection.provider_connection_id"),
        nullable=False,
        index=True,
    )
    channel_code: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    contact_id: Mapped[UUID | None] = mapped_column(StringUUID, nullable=True)
    recipient_address: Mapped[str] = mapped_column(Text, nullable=False)
    rendered_payload: Mapped[dict[str, Any]] = mapped_column(
        PortableJSON,
        nullable=False,
        default=dict,
    )
    provider_request_payload: Mapped[dict[str, Any]] = mapped_column(
        PortableJSON,
        nullable=False,
        default=dict,
    )
    external_message_id: Mapped[str | None] = mapped_column(
        Text, nullable=True, index=True
    )
    external_status: Mapped[str | None] = mapped_column(Text, nullable=True)
    internal_status: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        server_default=sa.text("'QUEUED'"),
        index=True,
    )
    error_code: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    queued_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    delivered_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    failed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.current_timestamp(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
        nullable=False,
    )


class DeliveryAttemptModel(Base):
    """SQLAlchemy model for provider send attempts."""

    __tablename__ = "communication_delivery_attempt"
    __table_args__ = (
        UniqueConstraint(
            "outbound_message_id",
            "attempt_no",
            name="uq_delivery_attempt",
        ),
    )

    delivery_attempt_id: Mapped[UUID] = mapped_column(
        StringUUID,
        primary_key=True,
        default=uuid6.uuid7,
        nullable=False,
    )
    outbound_message_id: Mapped[UUID] = mapped_column(
        StringUUID,
        ForeignKey("communication_outbound_message.outbound_message_id"),
        nullable=False,
        index=True,
    )
    provider_connection_id: Mapped[UUID] = mapped_column(
        StringUUID,
        ForeignKey("communication_provider_connection.provider_connection_id"),
        nullable=False,
    )
    attempt_no: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    request_payload: Mapped[dict[str, Any] | None] = mapped_column(
        PortableJSON, nullable=True
    )
    response_payload: Mapped[dict[str, Any] | None] = mapped_column(
        PortableJSON, nullable=True
    )
    http_status_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    external_message_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_code: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.current_timestamp(),
        nullable=False,
    )
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )


class DeliveryEventModel(Base):
    """SQLAlchemy model for provider status events."""

    __tablename__ = "communication_delivery_event"

    delivery_event_id: Mapped[UUID] = mapped_column(
        StringUUID,
        primary_key=True,
        default=uuid6.uuid7,
        nullable=False,
    )
    tenant_id: Mapped[UUID] = mapped_column(StringUUID, nullable=False, index=True)
    outbound_message_id: Mapped[UUID | None] = mapped_column(
        StringUUID,
        ForeignKey("communication_outbound_message.outbound_message_id"),
        nullable=True,
        index=True,
    )
    provider_connection_id: Mapped[UUID | None] = mapped_column(
        StringUUID,
        ForeignKey("communication_provider_connection.provider_connection_id"),
        nullable=True,
    )
    external_message_id: Mapped[str | None] = mapped_column(
        Text, nullable=True, index=True
    )
    external_status: Mapped[str | None] = mapped_column(Text, nullable=True)
    internal_status: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    event_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    raw_payload: Mapped[dict[str, Any]] = mapped_column(
        PortableJSON,
        nullable=False,
        default=dict,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.current_timestamp(),
        nullable=False,
    )


__all__ = [
    "CommunicationRequestModel",
    "DeliveryAttemptModel",
    "DeliveryEventModel",
    "MessageTemplateModel",
    "OutboundMessageModel",
    "ProviderConnectionModel",
    "ProviderConnectorDefinitionModel",
    "ProviderMessageTypeModel",
    "TemplateVersionModel",
]
