from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime
from typing import Any

from src.modules.communication.domain.delivery import (
    DeliveryAttempt,
    DeliveryAttemptIdVO,
    DeliveryAttemptNotFoundError,
    DeliveryEvent,
    DeliveryRepositoryProtocol,
)
from src.modules.communication.application.delivery.dto import (
    DeliveryAttemptDTO,
    DeliveryEventDTO,
)
from src.modules.communication.application.outbound_message.integration_events import (
    build_delivery_status_events,
)
from src.modules.communication.domain.outbound_message import (
    OutboundMessage,
    OutboundMessageIdVO,
    OutboundMessageStatus,
)
from src.modules.communication.domain.provider_connector import (
    ConnectorStatus,
    ProviderConnector,
    ProviderConnectorCodeVO,
)
from src.modules.communication.infrastructure.delivery.row_mapper import (
    delivery_attempt_dto,
    delivery_attempt_entity,
    delivery_event_dto,
    delivery_event_entity,
)
from src.modules.communication.infrastructure.outbound_message.row_mapper import (
    outbound_message_entity,
)
from src.modules.communication.infrastructure.provider_connector.row_mapper import (
    provider_connector_entity,
)
from src.modules.communication.infrastructure.runtime_object_names import (
    _ATTEMPT,
    _CONNECTOR,
    _EVENT,
    _OUTBOUND,
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
from src.modules.shared.application.events import OutboxRepositoryProtocol


class DeliveryRuntimeRepository(DeliveryRepositoryProtocol):
    """Runtime repository delivery aggregate."""

    _ATTEMPT_OBJECT_NAME = _ATTEMPT
    _EVENT_OBJECT_NAME = _EVENT

    def __init__(
        self,
        *,
        runtime_object_resolver: RuntimeObjectResolverProtocol,
        runtime_command_gateway: RuntimeCommandGateway,
        runtime_query_gateway: RuntimeQueryGateway,
        outbox_repository: OutboxRepositoryProtocol | None = None,
    ) -> None:
        """Инициализирует repository resolver-ом descriptor и runtime gateways."""
        self._runtime_object_resolver = runtime_object_resolver
        self._runtime_command_gateway = runtime_command_gateway
        self._runtime_query_gateway = runtime_query_gateway
        self._outbox_repository = outbox_repository
        self._filter_builder = RuntimeTypedFilterBuilder()

    async def get_delivery_attempt(
        self,
        *,
        tenant_id: EntityIdVO,
        delivery_attempt_id: DeliveryAttemptIdVO,
    ) -> DeliveryAttempt | None:
        """Загружает delivery attempt из runtime-таблицы."""
        row = await self._get(
            tenant_id=tenant_id,
            object_name=self._ATTEMPT_OBJECT_NAME,
            object_id=delivery_attempt_id.uuid,
        )
        if row is None:
            return None
        return delivery_attempt_entity(row)

    async def list_delivery_attempts(
        self,
        *,
        tenant_id: EntityIdVO,
        limit: int,
        offset: int,
        outbound_message_id: OutboundMessageIdVO | None = None,
        status: str | None = None,
    ) -> list[DeliveryAttemptDTO]:
        """Возвращает страницу delivery attempts."""
        tenant_vo = _entity_id(tenant_id)
        descriptor = await self._resolve_descriptor(
            tenant_vo,
            self._ATTEMPT_OBJECT_NAME,
        )
        filters: list[TypedFilterExpression] = []
        if outbound_message_id is not None:
            filters.append(
                self._filter_builder.condition(
                    descriptor=descriptor,
                    field="outbound_message_id",
                    op="eq",
                    value=_outbound_message_id(outbound_message_id).uuid,
                )
            )
        if status is not None:
            filters.append(
                self._filter_builder.condition(
                    descriptor=descriptor,
                    field="status",
                    op="eq",
                    value=status,
                )
            )
        rows = await self._list(
            descriptor=descriptor,
            filters=tuple(filters),
            sorting=(SortSpec("started_at", "desc"),),
            limit=limit,
            offset=offset,
        )
        return [delivery_attempt_dto(tenant_id=tenant_vo, row=row) for row in rows]

    async def list_delivery_events(
        self,
        *,
        tenant_id: EntityIdVO,
        limit: int,
        offset: int,
        outbound_message_id: OutboundMessageIdVO | None = None,
        external_message_id: str | None = None,
        internal_status: str | None = None,
        event_type: str | None = None,
    ) -> list[DeliveryEventDTO]:
        """Возвращает страницу delivery events."""
        tenant_vo = _entity_id(tenant_id)
        descriptor = await self._resolve_descriptor(
            tenant_vo,
            self._EVENT_OBJECT_NAME,
        )
        filters: list[TypedFilterExpression] = []
        if outbound_message_id is not None:
            filters.append(
                self._filter_builder.condition(
                    descriptor=descriptor,
                    field="outbound_message_id",
                    op="eq",
                    value=_outbound_message_id(outbound_message_id).uuid,
                )
            )
        if external_message_id is not None:
            filters.append(
                self._filter_builder.condition(
                    descriptor=descriptor,
                    field="external_message_id",
                    op="eq",
                    value=external_message_id,
                )
            )
        if internal_status is not None:
            filters.append(
                self._filter_builder.condition(
                    descriptor=descriptor,
                    field="internal_status",
                    op="eq",
                    value=internal_status,
                )
            )
        if event_type is not None:
            filters.append(
                self._filter_builder.condition(
                    descriptor=descriptor,
                    field="event_type",
                    op="eq",
                    value=event_type,
                )
            )
        rows = await self._list(
            descriptor=descriptor,
            filters=tuple(filters),
            sorting=(SortSpec("created_at", "desc"),),
            limit=limit,
            offset=offset,
        )
        return [delivery_event_dto(tenant_id=tenant_vo, row=row) for row in rows]

    async def next_attempt_no(
        self,
        *,
        tenant_id: EntityIdVO,
        outbound_message_id: OutboundMessageIdVO,
    ) -> int:
        """Возвращает следующий attempt_no для outbound message."""
        descriptor = await self._resolve_descriptor(
            tenant_id,
            self._ATTEMPT_OBJECT_NAME,
        )
        rows = await self._list(
            descriptor=descriptor,
            filters=(
                self._filter_builder.condition(
                    descriptor=descriptor,
                    field="outbound_message_id",
                    op="eq",
                    value=outbound_message_id.uuid,
                ),
            ),
            sorting=(SortSpec("attempt_no", "desc"),),
            limit=1,
        )
        return int(rows[0]["attempt_no"] if rows else 0) + 1

    async def save_delivery_attempt(
        self,
        *,
        tenant_id: EntityIdVO,
        attempt: DeliveryAttempt,
    ) -> DeliveryAttempt:
        """Создает или обновляет runtime row delivery attempt."""
        descriptor = await self._resolve_descriptor(
            tenant_id,
            self._ATTEMPT_OBJECT_NAME,
        )
        payload = _attempt_payload(attempt)
        existing = await self._runtime_query_gateway.get_by_id(
            descriptor=descriptor,
            object_id=attempt.delivery_attempt_id.uuid,
        )
        if existing is None:
            row = await self._runtime_command_gateway.insert(
                descriptor=descriptor,
                payload={"id": attempt.delivery_attempt_id.uuid, **payload},
            )
        else:
            patch = {
                key: value for key, value in payload.items() if key != "started_at"
            }
            row = await self._runtime_command_gateway.update(
                descriptor=descriptor,
                object_id=attempt.delivery_attempt_id.uuid,
                patch=patch,
            )
            if row is None:
                raise DeliveryAttemptNotFoundError("Delivery attempt was not found.")
        return delivery_attempt_entity(row)

    async def add_delivery_event(
        self,
        *,
        tenant_id: EntityIdVO,
        event: DeliveryEvent,
    ) -> DeliveryEvent:
        """Создает runtime row delivery event."""
        row = await self._runtime_command_gateway.insert(
            descriptor=await self._resolve_descriptor(
                tenant_id,
                self._EVENT_OBJECT_NAME,
            ),
            payload={
                "id": event.delivery_event_id.uuid,
                "created_at": event.created_at,
                "outbound_message_id": (
                    None
                    if event.outbound_message_id is None
                    else event.outbound_message_id.uuid
                ),
                "provider_connection_id": (
                    None
                    if event.provider_connection_id is None
                    else event.provider_connection_id.uuid
                ),
                "external_message_id": event.external_message_id,
                "external_status": event.external_status,
                "internal_status": event.internal_status,
                "event_type": event.event_type,
                "event_at": event.event_at,
                "raw_payload": dict(event.raw_payload),
            },
        )
        return delivery_event_entity(tenant_id=tenant_id, row=row)

    async def update_outbound_status_from_event(
        self,
        *,
        tenant_id: EntityIdVO,
        outbound_message_id: OutboundMessageIdVO,
        external_status: str | None,
        internal_status: str,
        now: datetime,
    ) -> None:
        """Обновляет outbound message status по delivery event."""
        outbound = await self._get_outbound_by_id(
            tenant_id=tenant_id,
            outbound_message_id=outbound_message_id,
        )
        if outbound is None:
            return
        await self._runtime_command_gateway.update(
            descriptor=await self._resolve_descriptor(tenant_id, _OUTBOUND),
            object_id=outbound_message_id.uuid,
            patch={
                "external_status": external_status,
                "internal_status": internal_status,
                **_status_timestamp_patch(outbound, internal_status, now),
            },
        )
        if self._outbox_repository is None:
            return
        for event in build_delivery_status_events(
            outbound=outbound,
            internal_status=internal_status,
            external_status=external_status,
            external_message_id=outbound.external_message_id,
            occurred_at=now,
        ):
            await self._outbox_repository.add(event)

    async def get_active_connector_by_code(
        self,
        *,
        tenant_id: EntityIdVO,
        provider_code: ProviderConnectorCodeVO,
    ) -> ProviderConnector | None:
        """Возвращает активный provider connector по коду."""
        descriptor = await self._resolve_descriptor(tenant_id, _CONNECTOR)
        rows = await self._list(
            descriptor=descriptor,
            filters=(
                self._filter_builder.condition(
                    descriptor=descriptor,
                    field="provider_code",
                    op="eq",
                    value=provider_code.value,
                ),
                self._filter_builder.condition(
                    descriptor=descriptor,
                    field="status",
                    op="eq",
                    value=ConnectorStatus.ACTIVE.value,
                ),
            ),
            sorting=(SortSpec("created_at", "desc"),),
            limit=1,
        )
        if not rows:
            return None
        return provider_connector_entity(rows[0])

    async def find_outbound_by_external_message_id(
        self,
        *,
        tenant_id: EntityIdVO,
        external_message_id: str,
    ) -> OutboundMessage | None:
        """Ищет outbound message по external provider id."""
        descriptor = await self._resolve_descriptor(tenant_id, _OUTBOUND)
        rows = await self._list(
            descriptor=descriptor,
            filters=(
                self._filter_builder.condition(
                    descriptor=descriptor,
                    field="external_message_id",
                    op="eq",
                    value=external_message_id,
                ),
            ),
            sorting=(SortSpec("created_at", "desc"),),
            limit=1,
        )
        if not rows:
            return None
        return outbound_message_entity(tenant_id=tenant_id, row=rows[0])

    async def _get_outbound_by_id(
        self,
        *,
        tenant_id: EntityIdVO,
        outbound_message_id: OutboundMessageIdVO,
    ) -> OutboundMessage | None:
        row = await self._get(
            tenant_id=tenant_id,
            object_name=_OUTBOUND,
            object_id=outbound_message_id.uuid,
        )
        if row is None:
            return None
        return outbound_message_entity(tenant_id=tenant_id, row=row)

    async def _get(
        self,
        *,
        tenant_id: EntityIdVO,
        object_name: str,
        object_id,
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

    async def _resolve_descriptor(self, tenant_id: EntityIdVO, object_name: str):
        """Получает runtime descriptor delivery-объекта для tenant."""
        return await self._runtime_object_resolver.resolve(
            tenant_id=tenant_id,
            object_name=object_name,
        )


def _attempt_payload(attempt: DeliveryAttempt) -> dict[str, Any]:
    return {
        "outbound_message_id": attempt.outbound_message_id.uuid,
        "provider_connection_id": attempt.provider_connection_id.uuid,
        "attempt_no": attempt.attempt_no,
        "status": attempt.status,
        "request_payload": (
            None if attempt.request_payload is None else dict(attempt.request_payload)
        ),
        "response_payload": (
            None if attempt.response_payload is None else dict(attempt.response_payload)
        ),
        "http_status_code": attempt.http_status_code,
        "external_message_id": attempt.external_message_id,
        "error_code": attempt.error_code,
        "error_message": attempt.error_message,
        "started_at": attempt.started_at,
        "finished_at": attempt.finished_at,
    }


def _entity_id(value: Any) -> EntityIdVO:
    if type(value) is EntityIdVO:
        return value
    return EntityIdVO.from_value(value)


def _outbound_message_id(value: Any) -> OutboundMessageIdVO:
    if type(value) is OutboundMessageIdVO:
        return value
    return OutboundMessageIdVO.from_value(value)


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


__all__ = ["DeliveryRuntimeRepository"]
