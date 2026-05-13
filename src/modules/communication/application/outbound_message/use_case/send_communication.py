from __future__ import annotations

from typing import Any, Protocol
from uuid import uuid4

from src.modules.communication.application.outbound_message.command import (
    SendCommunicationCommand,
)
from src.modules.communication.application.outbound_message.dto import (
    SendCommunicationResultDTO,
)
from src.modules.communication.application.services import JsonSchemaValidationService
from src.modules.communication.domain.error import CommunicationValidationError
from src.modules.communication.domain.message_template import (
    MessageTemplateCodeVO,
    MessageTemplateEntity,
    MessageTemplateIdVO,
    MessageTemplateNotFoundError,
    TemplateVersionEntity,
)
from src.modules.communication.domain.outbound_message import (
    CommunicationRequestIdVO,
    OutboundMessageIdVO,
    OutboundMessageRepositoryProtocol,
    OutboundMessageService,
)
from src.modules.communication.domain.provider_connection import (
    ProviderConnectionEntity,
)
from src.modules.communication.domain.provider_connection.value_object import (
    ProviderConnectionIdVO,
)
from src.modules.communication.domain.provider_connector import ProviderConnectorIdVO
from src.modules.shared import EntityIdVO


class SendCommunicationTemplateLookupProtocol(Protocol):
    """Порт lookup template данных для send-сценария."""

    async def get_template(
        self,
        *,
        tenant_id: EntityIdVO,
        template_id: MessageTemplateIdVO,
    ) -> MessageTemplateEntity | None:
        """Возвращает message template по id."""
        ...

    async def get_template_by_code(
        self,
        *,
        tenant_id: EntityIdVO,
        template_code: MessageTemplateCodeVO,
    ) -> MessageTemplateEntity | None:
        """Возвращает message template по tenant-local code."""
        ...

    async def get_active_template_version(
        self,
        tenant_id: EntityIdVO,
        template_id: MessageTemplateIdVO,
    ) -> TemplateVersionEntity | None:
        """Возвращает active template version."""
        ...


class ProviderConnectionLookupProtocol(Protocol):
    """Порт lookup active provider connection для send-сценария."""

    async def find_active_connection(
        self,
        *,
        tenant_id: EntityIdVO,
        provider_connector_id: ProviderConnectorIdVO,
        channel_code: str,
    ) -> ProviderConnectionEntity | None:
        """Ищет active provider connection по connector и channel."""
        ...


class SendCommunicationUseCase:
    """Use case постановки outbound message на отправку."""

    def __init__(
        self,
        *,
        repository: OutboundMessageRepositoryProtocol,
        service: OutboundMessageService,
        template_lookup: SendCommunicationTemplateLookupProtocol,
        schema_validator: JsonSchemaValidationService,
        provider_connection_lookup: ProviderConnectionLookupProtocol,
    ) -> None:
        """Инициализирует use case repository, service и lookup-портами."""
        self._repository = repository
        self._service = service
        self._template_lookup = template_lookup
        self._schema_validator = schema_validator
        self._provider_connection_lookup = provider_connection_lookup

    async def __call__(
        self,
        command: SendCommunicationCommand,
    ) -> SendCommunicationResultDTO:
        """Создает send request и outbound message либо возвращает idempotent hit."""
        tenant_id = _entity_id(command.tenant_id)
        if command.template_id is None and command.template_code is None:
            raise CommunicationValidationError(
                "Either template_id or template_code is required."
            )
        if command.idempotency_key:
            existing = await self._repository.get_existing_send_by_idempotency(
                tenant_id=tenant_id,
                idempotency_key=command.idempotency_key,
            )
            if existing is not None:
                request, outbound = existing
                return SendCommunicationResultDTO(
                    communication_request_id=request.communication_request_id.uuid,
                    outbound_message_id=outbound.outbound_message_id.uuid,
                    status=request.status,
                    internal_status=outbound.internal_status,
                    idempotent=True,
                )

        if command.template_id is not None:
            template = await self._template_lookup.get_template(
                tenant_id=tenant_id,
                template_id=_template_id(command.template_id),
            )
        else:
            assert command.template_code is not None
            template = await self._template_lookup.get_template_by_code(
                tenant_id=tenant_id,
                template_code=MessageTemplateCodeVO(command.template_code),
            )
        if template is None:
            raise MessageTemplateNotFoundError()
        if template.channel_code.value != command.channel_code:
            raise CommunicationValidationError(
                "Send channel must match template channel."
            )
        active_version = await self._template_lookup.get_active_template_version(
            tenant_id,
            template.template_id,
        )
        if active_version is None:
            raise CommunicationValidationError(
                "Message template does not have an active version."
            )
        self._schema_validator.validate(
            command.variables,
            active_version.variables_schema,
            "variables",
        )
        connection = await self._provider_connection_lookup.find_active_connection(
            tenant_id=tenant_id,
            provider_connector_id=template.provider_connector_id,
            channel_code=template.channel_code.value,
        )
        if connection is None:
            raise CommunicationValidationError(
                "No active provider connection found for template channel."
            )

        request, outbound = await self._service.create_send_request(
            tenant_id=tenant_id,
            communication_request_id=_communication_request_id(
                command.communication_request_id
            ),
            outbound_message_id=_outbound_message_id(command.outbound_message_id),
            initiator_type=command.initiator_type,
            initiator_ref_id=command.initiator_ref_id,
            correlation_id=(
                None
                if command.correlation_id is None
                else _entity_id(command.correlation_id)
            ),
            idempotency_key=command.idempotency_key,
            message_class=command.message_class,
            channel_code=command.channel_code,
            template_id=template.template_id,
            template_version_id=active_version.template_version_id,
            contact_id=(
                None if command.contact_id is None else _entity_id(command.contact_id)
            ),
            recipient_address=command.recipient_address,
            recipient_snapshot=command.recipient_snapshot,
            variables=command.variables,
            scheduled_at=command.scheduled_at,
            priority=command.priority,
            provider_connection_id=_provider_connection_id(
                connection.provider_connection_id
            ),
        )
        return SendCommunicationResultDTO(
            communication_request_id=request.communication_request_id.uuid,
            outbound_message_id=outbound.outbound_message_id.uuid,
            status=request.status,
            internal_status=outbound.internal_status,
            idempotent=False,
        )


def _entity_id(value: Any) -> EntityIdVO:
    if type(value) is EntityIdVO:
        return value
    return EntityIdVO.from_value(value)


def _template_id(value: Any) -> MessageTemplateIdVO:
    if type(value) is MessageTemplateIdVO:
        return value
    return MessageTemplateIdVO.from_value(value)


def _communication_request_id(value: Any) -> CommunicationRequestIdVO:
    if value is None:
        return CommunicationRequestIdVO.from_value(uuid4())
    if type(value) is CommunicationRequestIdVO:
        return value
    return CommunicationRequestIdVO.from_value(value)


def _outbound_message_id(value: Any) -> OutboundMessageIdVO:
    if value is None:
        return OutboundMessageIdVO.from_value(uuid4())
    if type(value) is OutboundMessageIdVO:
        return value
    return OutboundMessageIdVO.from_value(value)


def _provider_connection_id(value: Any) -> ProviderConnectionIdVO:
    if type(value) is ProviderConnectionIdVO:
        return value
    return ProviderConnectionIdVO.from_value(value)


__all__ = [
    "ProviderConnectionLookupProtocol",
    "SendCommunicationTemplateLookupProtocol",
    "SendCommunicationUseCase",
]
