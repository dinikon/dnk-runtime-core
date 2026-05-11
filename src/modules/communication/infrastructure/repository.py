from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.communication.application.dto import (
    MessageTemplateDTO,
    OutboundMessageDTO,
    ProviderConnectionDTO,
    ProviderConnectorDTO,
    ProviderMessageTypeDTO,
    TemplateVersionDTO,
)
from src.modules.communication.domain import (
    AttemptStatus,
    ConnectorStatus,
    OutboundMessageStatus,
    ProviderConnectionStatus,
    RequestStatus,
    TemplateStatus,
    TemplateVersionStatus,
)
from src.modules.communication.infrastructure.persistence import (
    CommunicationRequestModel,
    DeliveryAttemptModel,
    DeliveryEventModel,
    MessageTemplateModel,
    OutboundMessageModel,
    ProviderConnectionModel,
    ProviderConnectorDefinitionModel,
    ProviderMessageTypeModel,
    TemplateVersionModel,
)


class CommunicationRepository:
    """SQLAlchemy repository for the communication bounded context."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def upsert_connector(
        self,
        *,
        provider_code: str,
        provider_name: str,
        version: str,
        connector_type: str,
        yaml_spec: dict[str, Any],
        yaml_checksum: str,
        status: str = ConnectorStatus.ACTIVE.value,
    ) -> ProviderConnectorDefinitionModel:
        """Insert or update a provider connector definition by provider/version."""
        model = (
            await self._session.scalars(
                select(ProviderConnectorDefinitionModel).where(
                    ProviderConnectorDefinitionModel.provider_code == provider_code,
                    ProviderConnectorDefinitionModel.version == version,
                )
            )
        ).one_or_none()
        if model is None:
            model = ProviderConnectorDefinitionModel(
                provider_code=provider_code,
                provider_name=provider_name,
                version=version,
                connector_type=connector_type,
                yaml_spec=yaml_spec,
                yaml_checksum=yaml_checksum,
                status=status,
            )
            self._session.add(model)
        else:
            model.provider_name = provider_name
            model.connector_type = connector_type
            model.yaml_spec = yaml_spec
            model.yaml_checksum = yaml_checksum
            model.status = status
        await self._session.flush()
        return model

    async def upsert_message_type(
        self,
        *,
        provider_connector_id: UUID,
        message_type_code: str,
        channel_code: str,
        name: str,
        field_schema: dict[str, Any],
        ui_schema: dict[str, Any],
        is_active: bool = True,
    ) -> ProviderMessageTypeModel:
        """Insert or update a provider message type by connector/code."""
        model = (
            await self._session.scalars(
                select(ProviderMessageTypeModel).where(
                    ProviderMessageTypeModel.provider_connector_id
                    == provider_connector_id,
                    ProviderMessageTypeModel.message_type_code == message_type_code,
                )
            )
        ).one_or_none()
        if model is None:
            model = ProviderMessageTypeModel(
                provider_connector_id=provider_connector_id,
                message_type_code=message_type_code,
                channel_code=channel_code,
                name=name,
                field_schema=field_schema,
                ui_schema=ui_schema,
                is_active=is_active,
            )
            self._session.add(model)
        else:
            model.channel_code = channel_code
            model.name = name
            model.field_schema = field_schema
            model.ui_schema = ui_schema
            model.is_active = is_active
        await self._session.flush()
        return model

    async def get_connector(
        self,
        provider_connector_id: UUID,
    ) -> ProviderConnectorDefinitionModel | None:
        return (
            await self._session.scalars(
                select(ProviderConnectorDefinitionModel).where(
                    ProviderConnectorDefinitionModel.provider_connector_id
                    == provider_connector_id
                )
            )
        ).one_or_none()

    async def get_active_connector_by_code(
        self,
        provider_code: str,
    ) -> ProviderConnectorDefinitionModel | None:
        return (
            await self._session.scalars(
                select(ProviderConnectorDefinitionModel)
                .where(
                    ProviderConnectorDefinitionModel.provider_code == provider_code,
                    ProviderConnectorDefinitionModel.status
                    == ConnectorStatus.ACTIVE.value,
                )
                .order_by(desc(ProviderConnectorDefinitionModel.created_at))
                .limit(1)
            )
        ).one_or_none()

    async def list_connectors(self) -> list[ProviderConnectorDefinitionModel]:
        return list(
            (
                await self._session.scalars(
                    select(ProviderConnectorDefinitionModel).order_by(
                        ProviderConnectorDefinitionModel.provider_code,
                        ProviderConnectorDefinitionModel.version,
                    )
                )
            ).all()
        )

    async def list_message_types(
        self,
        provider_connector_id: UUID | None = None,
    ) -> list[ProviderMessageTypeModel]:
        statement = select(ProviderMessageTypeModel).order_by(
            ProviderMessageTypeModel.channel_code,
            ProviderMessageTypeModel.message_type_code,
        )
        if provider_connector_id is not None:
            statement = statement.where(
                ProviderMessageTypeModel.provider_connector_id == provider_connector_id
            )
        return list((await self._session.scalars(statement)).all())

    async def get_message_type(
        self,
        provider_message_type_id: UUID,
    ) -> ProviderMessageTypeModel | None:
        return (
            await self._session.scalars(
                select(ProviderMessageTypeModel).where(
                    ProviderMessageTypeModel.provider_message_type_id
                    == provider_message_type_id
                )
            )
        ).one_or_none()

    async def create_connection(
        self,
        *,
        tenant_id: UUID,
        provider_connector_id: UUID,
        connection_code: str,
        connection_name: str,
        channel_code: str,
        config: dict[str, Any],
        secret_ref: str | None,
        secrets_b64: str | None,
        status: str = ProviderConnectionStatus.ACTIVE.value,
    ) -> ProviderConnectionModel:
        model = ProviderConnectionModel(
            tenant_id=tenant_id,
            provider_connector_id=provider_connector_id,
            connection_code=connection_code,
            connection_name=connection_name,
            channel_code=channel_code,
            config=config,
            secret_ref=secret_ref,
            secrets_b64=secrets_b64,
            status=status,
        )
        self._session.add(model)
        await self._session.flush()
        return model

    async def list_connections(self, tenant_id: UUID) -> list[ProviderConnectionModel]:
        return list(
            (
                await self._session.scalars(
                    select(ProviderConnectionModel)
                    .where(ProviderConnectionModel.tenant_id == tenant_id)
                    .order_by(ProviderConnectionModel.connection_code)
                )
            ).all()
        )

    async def get_connection(
        self,
        provider_connection_id: UUID,
    ) -> ProviderConnectionModel | None:
        return (
            await self._session.scalars(
                select(ProviderConnectionModel).where(
                    ProviderConnectionModel.provider_connection_id
                    == provider_connection_id
                )
            )
        ).one_or_none()

    async def find_active_connection(
        self,
        *,
        tenant_id: UUID,
        provider_connector_id: UUID,
        channel_code: str,
    ) -> ProviderConnectionModel | None:
        return (
            await self._session.scalars(
                select(ProviderConnectionModel)
                .where(
                    ProviderConnectionModel.tenant_id == tenant_id,
                    ProviderConnectionModel.provider_connector_id
                    == provider_connector_id,
                    ProviderConnectionModel.channel_code == channel_code,
                    ProviderConnectionModel.status
                    == ProviderConnectionStatus.ACTIVE.value,
                )
                .order_by(ProviderConnectionModel.created_at)
                .limit(1)
            )
        ).one_or_none()

    async def create_template(
        self,
        *,
        tenant_id: UUID,
        template_code: str,
        name: str,
        description: str | None,
        provider_connector_id: UUID,
        provider_message_type_id: UUID,
        channel_code: str,
        message_class: str,
        status: str = TemplateStatus.DRAFT.value,
    ) -> MessageTemplateModel:
        model = MessageTemplateModel(
            tenant_id=tenant_id,
            template_code=template_code,
            name=name,
            description=description,
            provider_connector_id=provider_connector_id,
            provider_message_type_id=provider_message_type_id,
            channel_code=channel_code,
            message_class=message_class,
            status=status,
        )
        self._session.add(model)
        await self._session.flush()
        return model

    async def get_template(
        self,
        *,
        tenant_id: UUID,
        template_id: UUID,
    ) -> MessageTemplateModel | None:
        return (
            await self._session.scalars(
                select(MessageTemplateModel).where(
                    MessageTemplateModel.tenant_id == tenant_id,
                    MessageTemplateModel.template_id == template_id,
                )
            )
        ).one_or_none()

    async def get_template_by_code(
        self,
        *,
        tenant_id: UUID,
        template_code: str,
    ) -> MessageTemplateModel | None:
        return (
            await self._session.scalars(
                select(MessageTemplateModel).where(
                    MessageTemplateModel.tenant_id == tenant_id,
                    MessageTemplateModel.template_code == template_code,
                )
            )
        ).one_or_none()

    async def list_templates(self, tenant_id: UUID) -> list[MessageTemplateModel]:
        return list(
            (
                await self._session.scalars(
                    select(MessageTemplateModel)
                    .where(MessageTemplateModel.tenant_id == tenant_id)
                    .order_by(MessageTemplateModel.template_code)
                )
            ).all()
        )

    async def create_template_version(
        self,
        *,
        template_id: UUID,
        template_payload: dict[str, Any],
        variables_schema: dict[str, Any],
    ) -> TemplateVersionModel:
        version_no = await self._next_template_version_no(template_id)
        model = TemplateVersionModel(
            template_id=template_id,
            version_no=version_no,
            template_payload=template_payload,
            variables_schema=variables_schema,
            status=TemplateVersionStatus.DRAFT.value,
        )
        self._session.add(model)
        await self._session.flush()
        return model

    async def get_template_version(
        self,
        template_version_id: UUID,
    ) -> TemplateVersionModel | None:
        return (
            await self._session.scalars(
                select(TemplateVersionModel).where(
                    TemplateVersionModel.template_version_id == template_version_id
                )
            )
        ).one_or_none()

    async def get_active_template_version(
        self,
        template_id: UUID,
    ) -> TemplateVersionModel | None:
        return (
            await self._session.scalars(
                select(TemplateVersionModel).where(
                    TemplateVersionModel.template_id == template_id,
                    TemplateVersionModel.status == TemplateVersionStatus.ACTIVE.value,
                )
            )
        ).one_or_none()

    async def activate_template_version(
        self,
        *,
        template: MessageTemplateModel,
        version: TemplateVersionModel,
        now: datetime,
    ) -> TemplateVersionModel:
        versions = list(
            (
                await self._session.scalars(
                    select(TemplateVersionModel).where(
                        TemplateVersionModel.template_id == template.template_id
                    )
                )
            ).all()
        )
        for item in versions:
            if item.template_version_id == version.template_version_id:
                item.status = TemplateVersionStatus.ACTIVE.value
                item.activated_at = now
            elif item.status == TemplateVersionStatus.ACTIVE.value:
                item.status = TemplateVersionStatus.DEPRECATED.value
        template.status = TemplateStatus.ACTIVE.value
        await self._session.flush()
        return version

    async def get_existing_send_by_idempotency(
        self,
        *,
        tenant_id: UUID,
        idempotency_key: str,
    ) -> tuple[CommunicationRequestModel, OutboundMessageModel] | None:
        request = (
            await self._session.scalars(
                select(CommunicationRequestModel).where(
                    CommunicationRequestModel.tenant_id == tenant_id,
                    CommunicationRequestModel.idempotency_key == idempotency_key,
                )
            )
        ).one_or_none()
        if request is None:
            return None
        outbound = (
            await self._session.scalars(
                select(OutboundMessageModel).where(
                    OutboundMessageModel.communication_request_id
                    == request.communication_request_id
                )
            )
        ).one_or_none()
        if outbound is None:
            return None
        return request, outbound

    async def create_send_request(
        self,
        *,
        tenant_id: UUID,
        initiator_type: str,
        initiator_ref_id: str | None,
        correlation_id: UUID | None,
        idempotency_key: str | None,
        message_class: str,
        channel_code: str,
        template_id: UUID,
        template_version_id: UUID,
        contact_id: UUID | None,
        recipient_address: str,
        recipient_snapshot: dict[str, Any],
        variables: dict[str, Any],
        scheduled_at: datetime | None,
        priority: int,
        provider_connection_id: UUID,
        now: datetime,
    ) -> tuple[CommunicationRequestModel, OutboundMessageModel]:
        request = CommunicationRequestModel(
            tenant_id=tenant_id,
            initiator_type=initiator_type,
            initiator_ref_id=initiator_ref_id,
            correlation_id=correlation_id,
            idempotency_key=idempotency_key,
            message_class=message_class,
            channel_code=channel_code,
            template_id=template_id,
            template_version_id=template_version_id,
            contact_id=contact_id,
            recipient_address=recipient_address,
            recipient_snapshot=recipient_snapshot,
            variables=variables,
            scheduled_at=scheduled_at,
            priority=priority,
            status=RequestStatus.QUEUED.value,
        )
        self._session.add(request)
        await self._session.flush()

        outbound = OutboundMessageModel(
            tenant_id=tenant_id,
            communication_request_id=request.communication_request_id,
            provider_connection_id=provider_connection_id,
            channel_code=channel_code,
            contact_id=contact_id,
            recipient_address=recipient_address,
            rendered_payload={},
            provider_request_payload={},
            internal_status=OutboundMessageStatus.QUEUED.value,
            queued_at=now,
        )
        self._session.add(outbound)
        await self._session.flush()
        return request, outbound

    async def claim_queued_messages(self, limit: int) -> list[OutboundMessageModel]:
        statement = (
            select(OutboundMessageModel)
            .join(
                CommunicationRequestModel,
                CommunicationRequestModel.communication_request_id
                == OutboundMessageModel.communication_request_id,
            )
            .where(
                OutboundMessageModel.internal_status
                == OutboundMessageStatus.QUEUED.value
            )
            .order_by(
                CommunicationRequestModel.priority,
                OutboundMessageModel.created_at,
            )
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
        return list((await self._session.scalars(statement)).all())

    async def load_processing_context(
        self,
        outbound_message_id: UUID,
    ) -> tuple[
        OutboundMessageModel,
        CommunicationRequestModel,
        MessageTemplateModel,
        TemplateVersionModel,
        ProviderConnectionModel,
        ProviderConnectorDefinitionModel,
    ]:
        outbound = (
            await self._session.scalars(
                select(OutboundMessageModel).where(
                    OutboundMessageModel.outbound_message_id == outbound_message_id
                )
            )
        ).one()
        request = (
            await self._session.scalars(
                select(CommunicationRequestModel).where(
                    CommunicationRequestModel.communication_request_id
                    == outbound.communication_request_id
                )
            )
        ).one()
        template = (
            await self._session.scalars(
                select(MessageTemplateModel).where(
                    MessageTemplateModel.template_id == request.template_id
                )
            )
        ).one()
        version = (
            await self._session.scalars(
                select(TemplateVersionModel).where(
                    TemplateVersionModel.template_version_id
                    == request.template_version_id
                )
            )
        ).one()
        connection = (
            await self._session.scalars(
                select(ProviderConnectionModel).where(
                    ProviderConnectionModel.provider_connection_id
                    == outbound.provider_connection_id
                )
            )
        ).one()
        connector = (
            await self._session.scalars(
                select(ProviderConnectorDefinitionModel).where(
                    ProviderConnectorDefinitionModel.provider_connector_id
                    == connection.provider_connector_id
                )
            )
        ).one()
        return outbound, request, template, version, connection, connector

    async def create_delivery_attempt(
        self,
        *,
        outbound_message_id: UUID,
        provider_connection_id: UUID,
        request_payload: dict[str, Any],
    ) -> DeliveryAttemptModel:
        attempt_no = await self._next_attempt_no(outbound_message_id)
        attempt = DeliveryAttemptModel(
            outbound_message_id=outbound_message_id,
            provider_connection_id=provider_connection_id,
            attempt_no=attempt_no,
            status=AttemptStatus.STARTED.value,
            request_payload=request_payload,
        )
        self._session.add(attempt)
        await self._session.flush()
        return attempt

    async def get_outbound(
        self,
        *,
        tenant_id: UUID,
        outbound_message_id: UUID,
    ) -> OutboundMessageModel | None:
        return (
            await self._session.scalars(
                select(OutboundMessageModel).where(
                    OutboundMessageModel.tenant_id == tenant_id,
                    OutboundMessageModel.outbound_message_id == outbound_message_id,
                )
            )
        ).one_or_none()

    async def list_outbound(
        self,
        *,
        tenant_id: UUID,
        limit: int,
        offset: int,
    ) -> list[OutboundMessageModel]:
        return list(
            (
                await self._session.scalars(
                    select(OutboundMessageModel)
                    .where(OutboundMessageModel.tenant_id == tenant_id)
                    .order_by(desc(OutboundMessageModel.created_at))
                    .limit(limit)
                    .offset(offset)
                )
            ).all()
        )

    async def find_outbound_by_external_message_id(
        self,
        external_message_id: str,
    ) -> OutboundMessageModel | None:
        return (
            await self._session.scalars(
                select(OutboundMessageModel)
                .where(OutboundMessageModel.external_message_id == external_message_id)
                .order_by(desc(OutboundMessageModel.created_at))
                .limit(1)
            )
        ).one_or_none()

    async def add_delivery_event(
        self,
        *,
        tenant_id: UUID,
        outbound_message_id: UUID,
        provider_connection_id: UUID,
        external_message_id: str | None,
        external_status: str | None,
        internal_status: str,
        event_type: str,
        event_at: datetime | None,
        raw_payload: dict[str, Any],
    ) -> DeliveryEventModel:
        event = DeliveryEventModel(
            tenant_id=tenant_id,
            outbound_message_id=outbound_message_id,
            provider_connection_id=provider_connection_id,
            external_message_id=external_message_id,
            external_status=external_status,
            internal_status=internal_status,
            event_type=event_type,
            event_at=event_at,
            raw_payload=raw_payload,
        )
        self._session.add(event)
        await self._session.flush()
        return event

    async def _next_template_version_no(self, template_id: UUID) -> int:
        current = await self._session.scalar(
            select(func.max(TemplateVersionModel.version_no)).where(
                TemplateVersionModel.template_id == template_id
            )
        )
        return int(current or 0) + 1

    async def _next_attempt_no(self, outbound_message_id: UUID) -> int:
        current = await self._session.scalar(
            select(func.max(DeliveryAttemptModel.attempt_no)).where(
                DeliveryAttemptModel.outbound_message_id == outbound_message_id
            )
        )
        return int(current or 0) + 1


def connector_to_dto(model: ProviderConnectorDefinitionModel) -> ProviderConnectorDTO:
    spec = model.yaml_spec or {}
    return ProviderConnectorDTO(
        provider_connector_id=model.provider_connector_id,
        provider_code=model.provider_code,
        provider_name=model.provider_name,
        version=model.version,
        connector_type=model.connector_type,
        channels=list(spec.get("channels") or []),
        config_schema=dict(spec.get("config_schema") or {}),
        secrets_schema=dict(spec.get("secrets_schema") or {}),
        status=model.status,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def message_type_to_dto(model: ProviderMessageTypeModel) -> ProviderMessageTypeDTO:
    return ProviderMessageTypeDTO(
        provider_message_type_id=model.provider_message_type_id,
        provider_connector_id=model.provider_connector_id,
        message_type_code=model.message_type_code,
        channel_code=model.channel_code,
        name=model.name,
        field_schema=model.field_schema,
        ui_schema=model.ui_schema,
        is_active=model.is_active,
    )


def connection_to_dto(model: ProviderConnectionModel) -> ProviderConnectionDTO:
    return ProviderConnectionDTO(
        provider_connection_id=model.provider_connection_id,
        tenant_id=model.tenant_id,
        provider_connector_id=model.provider_connector_id,
        connection_code=model.connection_code,
        connection_name=model.connection_name,
        channel_code=model.channel_code,
        config=model.config,
        secret_ref=model.secret_ref,
        has_secrets=bool(model.secrets_b64),
        status=model.status,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def template_to_dto(
    model: MessageTemplateModel,
    active_version: TemplateVersionModel | None = None,
) -> MessageTemplateDTO:
    return MessageTemplateDTO(
        template_id=model.template_id,
        tenant_id=model.tenant_id,
        template_code=model.template_code,
        name=model.name,
        description=model.description,
        provider_connector_id=model.provider_connector_id,
        provider_message_type_id=model.provider_message_type_id,
        channel_code=model.channel_code,
        message_class=model.message_class,
        status=model.status,
        created_at=model.created_at,
        updated_at=model.updated_at,
        active_version_id=(
            active_version.template_version_id if active_version is not None else None
        ),
        active_version_no=(
            active_version.version_no if active_version is not None else None
        ),
    )


def template_version_to_dto(model: TemplateVersionModel) -> TemplateVersionDTO:
    return TemplateVersionDTO(
        template_version_id=model.template_version_id,
        template_id=model.template_id,
        version_no=model.version_no,
        template_payload=model.template_payload,
        variables_schema=model.variables_schema,
        status=model.status,
        created_at=model.created_at,
        activated_at=model.activated_at,
    )


def outbound_to_dto(model: OutboundMessageModel) -> OutboundMessageDTO:
    return OutboundMessageDTO(
        outbound_message_id=model.outbound_message_id,
        tenant_id=model.tenant_id,
        communication_request_id=model.communication_request_id,
        provider_connection_id=model.provider_connection_id,
        channel_code=model.channel_code,
        contact_id=model.contact_id,
        recipient_address=model.recipient_address,
        rendered_payload=model.rendered_payload,
        provider_request_payload=model.provider_request_payload,
        external_message_id=model.external_message_id,
        external_status=model.external_status,
        internal_status=model.internal_status,
        error_code=model.error_code,
        error_message=model.error_message,
        queued_at=model.queued_at,
        sent_at=model.sent_at,
        delivered_at=model.delivered_at,
        failed_at=model.failed_at,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def utc_now() -> datetime:
    return datetime.now(UTC)


def ensure_sequence(value: Sequence[Any] | None) -> list[Any]:
    return list(value or [])


__all__ = [
    "CommunicationRepository",
    "connection_to_dto",
    "connector_to_dto",
    "ensure_sequence",
    "message_type_to_dto",
    "outbound_to_dto",
    "template_to_dto",
    "template_version_to_dto",
    "utc_now",
]
