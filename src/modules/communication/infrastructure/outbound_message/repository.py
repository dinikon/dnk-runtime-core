from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

from src.modules.communication.domain.message_template import (
    MessageTemplateEntity,
    MessageTemplateIdVO,
    TemplateVersionEntity,
    TemplateVersionStatusVO,
)
from src.modules.communication.domain.outbound_message import (
    CommunicationRequest,
    CommunicationRequestIdVO,
    IdempotencyKeyVO,
    OutboundMessage,
    OutboundMessageIdVO,
    OutboundMessageStatus,
    RecipientIdentifierTypeVO,
    RequestStatus,
)
from src.modules.communication.domain.provider_connection import (
    ProviderConnectionEntity,
    ProviderConnectionIdVO,
    ProviderConnectionStatusVO,
)
from src.modules.communication.domain.provider_connector import (
    ConnectorStatus,
    ProviderConnector,
    ProviderConnectorIdVO,
    ProviderMessageType,
)
from src.modules.communication.infrastructure.message_template.row_mapper import (
    message_template_entity,
    provider_connector_entity,
    provider_message_type_entity,
    template_version_entity,
)
from src.modules.communication.infrastructure.outbound_message.row_mapper import (
    as_uuid,
    communication_request_entity,
    outbound_message_dto,
    outbound_message_entity,
)
from src.modules.communication.infrastructure.provider_connection.row_mapper import (
    provider_connection_entity,
)
from src.modules.communication.infrastructure.runtime_object_names import (
    _CONNECTION,
    _CONNECTOR,
    _MESSAGE_TYPE,
    _OUTBOUND,
    _REQUEST,
    _TEMPLATE,
    _TEMPLATE_VERSION,
)
from src.modules.runtime_data.application.models import (
    PageSpec,
    SortSpec,
    TypedFilterExpression,
)
from src.modules.runtime_data.application.ports import (
    RuntimeCommandGateway,
    RuntimeQueryGateway,
)
from src.modules.runtime_data.application.query.typed_filter_builder import (
    RuntimeTypedFilterBuilder,
)
from src.modules.schema_registry.runtime import RuntimeObjectDescriptor
from src.modules.schema_registry.runtime import RuntimeObjectResolverProtocol
from src.modules.shared import EntityIdVO


class OutboundMessageRuntimeRepository:
    """Runtime repository outbound message aggregate."""

    _OBJECT_NAME = _OUTBOUND

    def __init__(
        self,
        *,
        runtime_object_resolver: RuntimeObjectResolverProtocol,
        runtime_command_gateway: RuntimeCommandGateway,
        runtime_query_gateway: RuntimeQueryGateway,
    ) -> None:
        """Инициализирует repository resolver-ом descriptor и runtime gateways."""
        self._runtime_object_resolver = runtime_object_resolver
        self._runtime_command_gateway = runtime_command_gateway
        self._runtime_query_gateway = runtime_query_gateway
        self._filter_builder = RuntimeTypedFilterBuilder()

    async def get_existing_send_by_idempotency(
        self,
        *,
        tenant_id: EntityIdVO,
        idempotency_key: str,
    ) -> tuple[CommunicationRequest, OutboundMessage] | None:
        """Возвращает существующий send request по idempotency key."""
        tenant_vo = _entity_id(tenant_id)
        idempotency_vo = IdempotencyKeyVO(idempotency_key)
        await self._runtime_command_gateway.acquire_advisory_xact_lock(
            _send_idempotency_lock_key(tenant_vo, idempotency_vo.value)
        )
        request_descriptor = await self._resolve_descriptor(tenant_vo, _REQUEST)
        requests = await self._list(
            descriptor=request_descriptor,
            filters=(
                self._filter_builder.condition(
                    descriptor=request_descriptor,
                    field="idempotency_key",
                    op="eq",
                    value=idempotency_vo.value,
                ),
            ),
            limit=1,
        )
        if not requests:
            return None
        outbound_descriptor = await self._resolve_descriptor(tenant_vo, _OUTBOUND)
        outbounds = await self._list(
            descriptor=outbound_descriptor,
            filters=(
                self._filter_builder.condition(
                    descriptor=outbound_descriptor,
                    field="communication_request_id",
                    op="eq",
                    value=requests[0]["id"],
                ),
            ),
            limit=1,
        )
        if not outbounds:
            return None
        return (
            communication_request_entity(tenant_id=tenant_vo, row=requests[0]),
            outbound_message_entity(tenant_id=tenant_vo, row=outbounds[0]),
        )

    async def get_template(
        self,
        *,
        tenant_id: EntityIdVO,
        template_id: MessageTemplateIdVO,
    ) -> MessageTemplateEntity | None:
        """Загружает message template entity для send-сценария."""
        tenant_vo = _entity_id(tenant_id)
        row = await self._get(
            tenant_id=tenant_vo,
            object_name=_TEMPLATE,
            object_id=_message_template_id(template_id).uuid,
        )
        if row is None:
            return None
        return message_template_entity(tenant_id=tenant_vo, row=row)

    async def get_active_template_version(
        self,
        tenant_id: EntityIdVO,
        template_id: MessageTemplateIdVO,
    ) -> TemplateVersionEntity | None:
        """Возвращает active template version для template."""
        tenant_vo = _entity_id(tenant_id)
        descriptor = await self._resolve_descriptor(tenant_vo, _TEMPLATE_VERSION)
        rows = await self._list(
            descriptor=descriptor,
            filters=(
                self._filter_builder.condition(
                    descriptor=descriptor,
                    field="template_id",
                    op="eq",
                    value=_message_template_id(template_id).uuid,
                ),
                self._filter_builder.condition(
                    descriptor=descriptor,
                    field="status",
                    op="eq",
                    value=TemplateVersionStatusVO.ACTIVE.value,
                ),
            ),
            limit=1,
        )
        if not rows:
            return None
        return template_version_entity(rows[0])

    async def find_active_connection(
        self,
        *,
        tenant_id: EntityIdVO,
        provider_connector_id: ProviderConnectorIdVO,
        channel_code: str,
    ) -> ProviderConnectionEntity | None:
        """Ищет active provider connection по connector и channel."""
        tenant_vo = _entity_id(tenant_id)
        connector_vo = _provider_connector_id(provider_connector_id)
        descriptor = await self._resolve_descriptor(tenant_vo, _CONNECTION)
        rows = await self._list(
            descriptor=descriptor,
            filters=(
                self._filter_builder.condition(
                    descriptor=descriptor,
                    field="provider_connector_id",
                    op="eq",
                    value=connector_vo.uuid,
                ),
                self._filter_builder.condition(
                    descriptor=descriptor,
                    field="channel_code",
                    op="eq",
                    value=channel_code,
                ),
                self._filter_builder.condition(
                    descriptor=descriptor,
                    field="status",
                    op="eq",
                    value=ProviderConnectionStatusVO.ACTIVE.value,
                ),
            ),
            sorting=(SortSpec("created_at"),),
            limit=1,
        )
        if not rows:
            return None
        connection = provider_connection_entity(tenant_id=tenant_vo, row=rows[0])
        connector_row = await self._get(
            tenant_id=tenant_vo,
            object_name=_CONNECTOR,
            object_id=connection.provider_connector_id.uuid,
        )
        if connector_row is None:
            return None
        connector = provider_connector_entity(connector_row)
        if connector.status != ConnectorStatus.ACTIVE.value:
            return None
        return connection

    async def create_send_request(
        self,
        *,
        tenant_id: EntityIdVO,
        communication_request_id: CommunicationRequestIdVO,
        outbound_message_id: OutboundMessageIdVO,
        initiator_type: str,
        initiator_ref_id: str,
        correlation_id: EntityIdVO,
        idempotency_key: str,
        channel_code: str,
        template_id: MessageTemplateIdVO,
        template_version_id,
        recipient_identifier_type: str,
        recipient_address: str,
        recipient_snapshot: dict[str, Any],
        variables: dict[str, Any],
        scheduled_at: datetime | None,
        priority: int,
        provider_connection_id: ProviderConnectionIdVO,
        now: datetime,
    ) -> tuple[CommunicationRequest, OutboundMessage]:
        """Создает communication request и queued outbound message runtime rows."""
        tenant_vo = _entity_id(tenant_id)
        request_vo = _communication_request_id(communication_request_id)
        outbound_vo = _outbound_message_id(outbound_message_id)
        idempotency_vo = IdempotencyKeyVO(idempotency_key)
        recipient_type_vo = RecipientIdentifierTypeVO(recipient_identifier_type)
        request = await self._insert(
            tenant_id=tenant_vo,
            object_name=_REQUEST,
            payload={
                "id": request_vo.uuid,
                "initiator_type": initiator_type,
                "initiator_ref_id": initiator_ref_id,
                "correlation_id": _entity_id(correlation_id).uuid,
                "idempotency_key": idempotency_vo.value,
                "channel_code": channel_code,
                "template_id": _message_template_id(template_id).uuid,
                "template_version_id": _id_uuid(template_version_id),
                "recipient_identifier_type": recipient_type_vo.value,
                "recipient_address": recipient_address,
                "recipient_snapshot": dict(recipient_snapshot),
                "variables": dict(variables),
                "scheduled_at": scheduled_at,
                "priority": priority,
                "status": RequestStatus.QUEUED.value,
            },
        )
        outbound = await self._insert(
            tenant_id=tenant_vo,
            object_name=_OUTBOUND,
            payload={
                "id": outbound_vo.uuid,
                "communication_request_id": request_vo.uuid,
                "provider_connection_id": _provider_connection_id(
                    provider_connection_id
                ).uuid,
                "channel_code": channel_code,
                "priority": priority,
                "recipient_identifier_type": recipient_type_vo.value,
                "recipient_address": recipient_address,
                "recipient_snapshot": dict(recipient_snapshot),
                "rendered_payload": {},
                "provider_request_payload": {},
                "internal_status": OutboundMessageStatus.QUEUED.value,
                "queued_at": now,
            },
        )
        return (
            communication_request_entity(tenant_id=tenant_vo, row=request),
            outbound_message_entity(tenant_id=tenant_vo, row=outbound),
        )

    async def claim_queued_messages(
        self,
        tenant_id: EntityIdVO,
        limit: int,
    ) -> list[OutboundMessage]:
        """Захватывает queued outbound messages для batch processing."""
        tenant_vo = _entity_id(tenant_id)
        claimed = []
        now = _utc_now()
        descriptor = await self._resolve_descriptor(tenant_vo, _OUTBOUND)
        for _ in range(limit):
            token = uuid4()
            rows = await self._claim_outbounds(
                descriptor=descriptor,
                filters=(
                    self._filter_builder.condition(
                        descriptor=descriptor,
                        field="internal_status",
                        op="eq",
                        value=OutboundMessageStatus.QUEUED.value,
                    ),
                    self._filter_builder.group(
                        logic="or",
                        items=(
                            self._filter_builder.condition(
                                descriptor=descriptor,
                                field="next_attempt_at",
                                op="eq",
                                value=None,
                            ),
                            self._filter_builder.condition(
                                descriptor=descriptor,
                                field="next_attempt_at",
                                op="lte",
                                value=now,
                            ),
                        ),
                    ),
                ),
                patch={
                    "internal_status": OutboundMessageStatus.SENDING.value,
                    "processing_token": token,
                    "processing_started_at": now,
                    "processing_deadline_at": now + timedelta(seconds=300),
                },
                limit=1,
            )
            if not rows:
                break
            claimed.append(outbound_message_entity(tenant_id=tenant_vo, row=rows[0]))
        return claimed

    async def list_publishable_outbounds(
        self,
        *,
        tenant_id: EntityIdVO,
        limit: int,
        now: datetime,
        republish_before: datetime,
    ) -> list[OutboundMessage]:
        """Возвращает queued outbound messages, которые нужно опубликовать."""
        tenant_vo = _entity_id(tenant_id)
        descriptor = await self._resolve_descriptor(tenant_vo, _OUTBOUND)
        rows = await self._list(
            descriptor=descriptor,
            filters=(
                self._filter_builder.condition(
                    descriptor=descriptor,
                    field="internal_status",
                    op="eq",
                    value=OutboundMessageStatus.QUEUED.value,
                ),
                self._filter_builder.group(
                    logic="or",
                    items=(
                        self._filter_builder.condition(
                            descriptor=descriptor,
                            field="next_attempt_at",
                            op="eq",
                            value=None,
                        ),
                        self._filter_builder.condition(
                            descriptor=descriptor,
                            field="next_attempt_at",
                            op="lte",
                            value=now,
                        ),
                    ),
                ),
                self._filter_builder.group(
                    logic="or",
                    items=(
                        self._filter_builder.condition(
                            descriptor=descriptor,
                            field="queue_published_at",
                            op="eq",
                            value=None,
                        ),
                        self._filter_builder.condition(
                            descriptor=descriptor,
                            field="queue_published_at",
                            op="lte",
                            value=republish_before,
                        ),
                    ),
                ),
            ),
            sorting=(SortSpec("priority"), SortSpec("created_at")),
            limit=limit,
        )
        return [outbound_message_entity(tenant_id=tenant_vo, row=row) for row in rows]

    async def mark_outbound_published(
        self,
        *,
        tenant_id: EntityIdVO,
        outbound_message_id: OutboundMessageIdVO,
        published_at: datetime,
    ) -> None:
        """Фиксирует публикацию outbound message в broker queue."""
        tenant_vo = _entity_id(tenant_id)
        outbound_id = _outbound_message_id(outbound_message_id)
        outbound = await self.get_outbound_by_id(tenant_vo, outbound_id)
        if outbound is None:
            return
        outbound.mark_published(published_at)
        await self._runtime_command_gateway.update(
            descriptor=await self._resolve_descriptor(tenant_vo, _OUTBOUND),
            object_id=outbound_id.uuid,
            patch={
                "queue_published_at": outbound.queue_published_at,
                "queue_publish_count": outbound.queue_publish_count,
            },
        )

    async def get_outbound_by_id(
        self,
        tenant_id: EntityIdVO,
        outbound_message_id: OutboundMessageIdVO,
    ) -> OutboundMessage | None:
        """Возвращает outbound message entity по id."""
        tenant_vo = _entity_id(tenant_id)
        row = await self._get(
            tenant_id=tenant_vo,
            object_name=_OUTBOUND,
            object_id=_outbound_message_id(outbound_message_id).uuid,
        )
        if row is None:
            return None
        return outbound_message_entity(tenant_id=tenant_vo, row=row)

    async def claim_outbound_for_processing(
        self,
        *,
        tenant_id: EntityIdVO,
        outbound_message_id: OutboundMessageIdVO,
        processing_token: EntityIdVO,
        now: datetime,
        lease_until: datetime,
    ) -> OutboundMessage | None:
        """Атомарно захватывает один queued outbound message по id."""
        tenant_vo = _entity_id(tenant_id)
        descriptor = await self._resolve_descriptor(tenant_vo, _OUTBOUND)
        rows = await self._claim_outbounds(
            descriptor=descriptor,
            filters=(
                self._filter_builder.condition(
                    descriptor=descriptor,
                    field="id",
                    op="eq",
                    value=_outbound_message_id(outbound_message_id).uuid,
                ),
                self._filter_builder.condition(
                    descriptor=descriptor,
                    field="internal_status",
                    op="eq",
                    value=OutboundMessageStatus.QUEUED.value,
                ),
                self._filter_builder.group(
                    logic="or",
                    items=(
                        self._filter_builder.condition(
                            descriptor=descriptor,
                            field="next_attempt_at",
                            op="eq",
                            value=None,
                        ),
                        self._filter_builder.condition(
                            descriptor=descriptor,
                            field="next_attempt_at",
                            op="lte",
                            value=now,
                        ),
                    ),
                ),
            ),
            patch={
                "internal_status": OutboundMessageStatus.SENDING.value,
                "processing_token": _entity_id(processing_token).uuid,
                "processing_started_at": now,
                "processing_deadline_at": lease_until,
            },
            limit=1,
        )
        if not rows:
            return None
        return outbound_message_entity(tenant_id=tenant_vo, row=rows[0])

    async def load_processing_context(
        self,
        tenant_id: EntityIdVO,
        outbound_message_id: OutboundMessageIdVO,
    ) -> tuple[
        OutboundMessage,
        CommunicationRequest,
        MessageTemplateEntity,
        TemplateVersionEntity,
        ProviderConnectionEntity,
        ProviderConnector,
        ProviderMessageType,
    ]:
        """Загружает entity context, нужный для provider send."""
        tenant_vo = _entity_id(tenant_id)
        outbound = await self.get_outbound_by_id(tenant_vo, outbound_message_id)
        if outbound is None:
            raise LookupError(
                f"Required communication runtime row '{_OUTBOUND}' was not found."
            )
        request = communication_request_entity(
            tenant_id=tenant_vo,
            row=await self._required(
                _REQUEST,
                await self._get(
                    tenant_id=tenant_vo,
                    object_name=_REQUEST,
                    object_id=outbound.communication_request_id.uuid,
                ),
            ),
        )
        template = message_template_entity(
            tenant_id=tenant_vo,
            row=await self._required(
                _TEMPLATE,
                await self._get(
                    tenant_id=tenant_vo,
                    object_name=_TEMPLATE,
                    object_id=request.template_id.uuid,
                ),
            ),
        )
        version = template_version_entity(
            await self._required(
                _TEMPLATE_VERSION,
                await self._get(
                    tenant_id=tenant_vo,
                    object_name=_TEMPLATE_VERSION,
                    object_id=request.template_version_id.uuid,
                ),
            )
        )
        connection = provider_connection_entity(
            tenant_id=tenant_vo,
            row=await self._required(
                _CONNECTION,
                await self._get(
                    tenant_id=tenant_vo,
                    object_name=_CONNECTION,
                    object_id=outbound.provider_connection_id.uuid,
                ),
            ),
        )
        connector = provider_connector_entity(
            await self._required(
                _CONNECTOR,
                await self._get(
                    tenant_id=tenant_vo,
                    object_name=_CONNECTOR,
                    object_id=connection.provider_connector_id.uuid,
                ),
            )
        )
        message_type = provider_message_type_entity(
            await self._required(
                _MESSAGE_TYPE,
                await self._get(
                    tenant_id=tenant_vo,
                    object_name=_MESSAGE_TYPE,
                    object_id=template.provider_message_type_id.uuid,
                ),
            )
        )
        return outbound, request, template, version, connection, connector, message_type

    async def complete_outbound_processing(
        self,
        *,
        tenant_id: EntityIdVO,
        outbound_message_id: OutboundMessageIdVO,
        processing_token: EntityIdVO,
        delivery_attempt_id,
        rendered_payload: dict[str, Any],
        provider_request_payload: dict[str, Any],
        response_payload: dict[str, Any],
        http_status_code: int | None,
        external_message_id: str | None,
        external_status: str | None,
        internal_status: str,
        finished_at: datetime,
    ) -> bool:
        """Фиксирует успешную provider processing операцию."""
        tenant_vo = _entity_id(tenant_id)
        outbound_id = _outbound_message_id(outbound_message_id)
        token = _entity_id(processing_token)
        outbound = await self.get_outbound_by_id(tenant_vo, outbound_id)
        if (
            outbound is None
            or outbound.processing_token is None
            or outbound.processing_token.uuid != token.uuid
        ):
            return False
        patch = {
            "rendered_payload": dict(rendered_payload),
            "provider_request_payload": dict(provider_request_payload),
            "external_message_id": external_message_id,
            "external_status": external_status,
            "internal_status": internal_status,
            "error_code": None,
            "error_message": None,
            "processing_token": None,
            "processing_started_at": None,
            "processing_deadline_at": None,
            "next_attempt_at": None,
            **_status_timestamp_patch(outbound, internal_status, finished_at),
        }
        outbound_descriptor = await self._resolve_descriptor(tenant_vo, _OUTBOUND)
        updated = await self._runtime_command_gateway.update_where(
            descriptor=outbound_descriptor,
            filters=(
                self._filter_builder.condition(
                    descriptor=outbound_descriptor,
                    field="id",
                    op="eq",
                    value=outbound_id.uuid,
                ),
                self._filter_builder.condition(
                    descriptor=outbound_descriptor,
                    field="processing_token",
                    op="eq",
                    value=token.uuid,
                ),
            ),
            patch=patch,
        )
        if not updated:
            return False
        await self._runtime_command_gateway.update(
            descriptor=await self._resolve_descriptor(tenant_vo, _REQUEST),
            object_id=outbound.communication_request_id.uuid,
            patch={"status": _request_status_for_internal_status(internal_status)},
        )
        return True

    async def fail_outbound_processing(
        self,
        *,
        tenant_id: EntityIdVO,
        outbound_message_id: OutboundMessageIdVO,
        processing_token: EntityIdVO,
        delivery_attempt_id,
        error_code: str,
        error_message: str,
        finished_at: datetime,
        response_payload: dict[str, Any] | None = None,
        http_status_code: int | None = None,
        external_message_id: str | None = None,
        external_status: str | None = None,
        retry_at: datetime | None = None,
    ) -> bool:
        """Фиксирует ошибку provider processing операции."""
        tenant_vo = _entity_id(tenant_id)
        outbound_id = _outbound_message_id(outbound_message_id)
        token = _entity_id(processing_token)
        outbound = await self.get_outbound_by_id(tenant_vo, outbound_id)
        if (
            outbound is None
            or outbound.processing_token is None
            or outbound.processing_token.uuid != token.uuid
        ):
            return False
        retryable = retry_at is not None
        outbound_patch = {
            "processing_token": None,
            "processing_started_at": None,
            "processing_deadline_at": None,
            "error_code": error_code,
            "error_message": error_message,
            "external_message_id": external_message_id,
            "external_status": external_status,
            "internal_status": (
                OutboundMessageStatus.QUEUED.value
                if retryable
                else OutboundMessageStatus.FAILED.value
            ),
            "next_attempt_at": retry_at,
            "queue_published_at": None if retryable else outbound.queue_published_at,
            "failed_at": None if retryable else (outbound.failed_at or finished_at),
        }
        outbound_descriptor = await self._resolve_descriptor(tenant_vo, _OUTBOUND)
        updated = await self._runtime_command_gateway.update_where(
            descriptor=outbound_descriptor,
            filters=(
                self._filter_builder.condition(
                    descriptor=outbound_descriptor,
                    field="id",
                    op="eq",
                    value=outbound_id.uuid,
                ),
                self._filter_builder.condition(
                    descriptor=outbound_descriptor,
                    field="processing_token",
                    op="eq",
                    value=token.uuid,
                ),
            ),
            patch=outbound_patch,
        )
        if not updated:
            return False
        await self._runtime_command_gateway.update(
            descriptor=await self._resolve_descriptor(tenant_vo, _REQUEST),
            object_id=outbound.communication_request_id.uuid,
            patch={
                "status": (
                    RequestStatus.QUEUED.value
                    if retryable
                    else RequestStatus.FAILED.value
                )
            },
        )
        return True

    async def recover_stuck_outbounds(
        self,
        *,
        tenant_id: EntityIdVO,
        older_than: datetime,
        now: datetime,
        limit: int,
    ) -> int:
        """Помечает истекшие SENDING messages как UNKNOWN."""
        tenant_vo = _entity_id(tenant_id)
        descriptor = await self._resolve_descriptor(tenant_vo, _OUTBOUND)
        rows = await self._claim_outbounds(
            descriptor=descriptor,
            filters=(
                self._filter_builder.condition(
                    descriptor=descriptor,
                    field="internal_status",
                    op="eq",
                    value=OutboundMessageStatus.SENDING.value,
                ),
                self._filter_builder.group(
                    logic="or",
                    items=(
                        self._filter_builder.condition(
                            descriptor=descriptor,
                            field="processing_deadline_at",
                            op="lte",
                            value=now,
                        ),
                        self._filter_builder.condition(
                            descriptor=descriptor,
                            field="processing_started_at",
                            op="lte",
                            value=older_than,
                        ),
                    ),
                ),
            ),
            patch={
                "internal_status": OutboundMessageStatus.UNKNOWN.value,
                "processing_token": None,
                "processing_started_at": None,
                "processing_deadline_at": None,
                "error_code": "PROCESSING_LEASE_EXPIRED",
                "error_message": "Processing lease expired before completion.",
                "failed_at": now,
            },
            limit=limit,
        )
        for row in rows:
            await self._runtime_command_gateway.update(
                descriptor=await self._resolve_descriptor(tenant_vo, _REQUEST),
                object_id=as_uuid(row["communication_request_id"]),
                patch={"status": RequestStatus.FAILED.value},
            )
        return len(rows)

    async def get_outbound(
        self,
        *,
        tenant_id: EntityIdVO,
        outbound_message_id: OutboundMessageIdVO,
    ):
        """Возвращает outbound message DTO по id."""
        tenant_vo = _entity_id(tenant_id)
        row = await self._get(
            tenant_id=tenant_vo,
            object_name=_OUTBOUND,
            object_id=_outbound_message_id(outbound_message_id).uuid,
        )
        if row is None:
            return None
        return outbound_message_dto(tenant_id=tenant_vo, row=row)

    async def list_outbound(
        self,
        *,
        tenant_id: EntityIdVO,
        limit: int,
        offset: int,
    ):
        """Возвращает страницу outbound message DTO."""
        tenant_vo = _entity_id(tenant_id)
        descriptor = await self._resolve_descriptor(tenant_vo, _OUTBOUND)
        rows = await self._list(
            descriptor=descriptor,
            sorting=(SortSpec("created_at", "desc"),),
            limit=limit,
            offset=offset,
        )
        return [outbound_message_dto(tenant_id=tenant_vo, row=row) for row in rows]

    async def _insert(
        self,
        *,
        tenant_id: EntityIdVO,
        object_name: str,
        payload: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        """Создает runtime row."""
        return await self._runtime_command_gateway.insert(
            descriptor=await self._resolve_descriptor(tenant_id, object_name),
            payload=payload,
        )

    async def _get(
        self,
        *,
        tenant_id: EntityIdVO,
        object_name: str,
        object_id: UUID,
    ) -> Mapping[str, Any] | None:
        """Возвращает runtime row по id."""
        return await self._runtime_query_gateway.get_by_id(
            descriptor=await self._resolve_descriptor(tenant_id, object_name),
            object_id=object_id,
        )

    async def _list(
        self,
        *,
        descriptor: RuntimeObjectDescriptor,
        filters: Sequence[TypedFilterExpression] = (),
        sorting: Sequence[SortSpec] = (),
        limit: int | None = None,
        offset: int = 0,
    ) -> list[Mapping[str, Any]]:
        """Возвращает runtime rows с фильтрами, сортировкой и page spec."""
        return await self._runtime_query_gateway.list(
            descriptor=descriptor,
            filters=filters,
            sorting=sorting,
            page=PageSpec(limit=limit, offset=offset) if limit is not None else None,
        )

    async def _claim_outbounds(
        self,
        *,
        descriptor: RuntimeObjectDescriptor,
        filters: Sequence[TypedFilterExpression],
        patch: Mapping[str, Any],
        limit: int,
    ) -> list[Mapping[str, Any]]:
        """Атомарно claim-ит outbound rows."""
        return await self._runtime_command_gateway.claim(
            descriptor=descriptor,
            filters=filters,
            patch=patch,
            sorting=(SortSpec("priority"), SortSpec("created_at")),
            limit=limit,
        )

    async def _resolve_descriptor(self, tenant_id: EntityIdVO, object_name: str):
        """Получает runtime descriptor communication-объекта для tenant."""
        return await self._runtime_object_resolver.resolve(
            tenant_id=tenant_id,
            object_name=object_name,
        )

    @staticmethod
    async def _required(label: str, row: Mapping[str, Any] | None) -> Mapping[str, Any]:
        """Возвращает row или поднимает ошибку неполного processing context."""
        if row is None:
            raise LookupError(
                f"Required communication runtime row '{label}' was not found."
            )
        return row


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _id_uuid(value: Any) -> UUID:
    if isinstance(value, UUID):
        return value
    if hasattr(value, "uuid"):
        return value.uuid
    raise TypeError("Communication id value must expose UUID.")


def _entity_id(value: Any) -> EntityIdVO:
    if type(value) is EntityIdVO:
        return value
    return EntityIdVO.from_value(value)


def _communication_request_id(value: Any) -> CommunicationRequestIdVO:
    if type(value) is CommunicationRequestIdVO:
        return value
    return CommunicationRequestIdVO.from_value(value)


def _outbound_message_id(value: Any) -> OutboundMessageIdVO:
    if type(value) is OutboundMessageIdVO:
        return value
    return OutboundMessageIdVO.from_value(value)


def _message_template_id(value: Any) -> MessageTemplateIdVO:
    if type(value) is MessageTemplateIdVO:
        return value
    return MessageTemplateIdVO.from_value(value)


def _provider_connection_id(value: Any) -> ProviderConnectionIdVO:
    if type(value) is ProviderConnectionIdVO:
        return value
    return ProviderConnectionIdVO.from_value(value)


def _provider_connector_id(value: Any) -> ProviderConnectorIdVO:
    if type(value) is ProviderConnectorIdVO:
        return value
    return ProviderConnectorIdVO.from_value(value)


def _send_idempotency_lock_key(tenant_id: EntityIdVO, idempotency_key: str) -> str:
    return f"communication_send_idempotency:{tenant_id.uuid}:{idempotency_key}"


def _request_status_for_internal_status(internal_status: str) -> str:
    if internal_status in {
        OutboundMessageStatus.SENT.value,
        OutboundMessageStatus.DELIVERED.value,
        OutboundMessageStatus.OPENED.value,
        OutboundMessageStatus.CLICKED.value,
    }:
        return RequestStatus.COMPLETED.value
    return RequestStatus.FAILED.value


def _status_timestamp_patch(
    outbound: OutboundMessage,
    internal_status: str,
    now: datetime,
) -> dict[str, Any]:
    if internal_status == OutboundMessageStatus.SENT.value:
        return {"sent_at": outbound.sent_at or now}
    if internal_status == OutboundMessageStatus.DELIVERED.value:
        return {
            "sent_at": outbound.sent_at or now,
            "delivered_at": outbound.delivered_at or now,
        }
    if internal_status in {
        OutboundMessageStatus.FAILED.value,
        OutboundMessageStatus.EXPIRED.value,
        OutboundMessageStatus.UNDELIVERED.value,
    }:
        return {"failed_at": outbound.failed_at or now}
    return {}


__all__ = ["OutboundMessageRuntimeRepository"]
