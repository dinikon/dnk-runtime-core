from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import Any
from uuid import UUID, uuid4

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
from src.modules.runtime_data import (
    FilterGroupSpec,
    FilterSpec,
    PageSpec,
    SortSpec,
)
from src.modules.runtime_data.application.ports import (
    RuntimeCommandGateway,
    RuntimeQueryGateway,
)
from src.modules.schema_registry.runtime import (
    RuntimeObjectDescriptor,
    RuntimeObjectResolverProtocol,
)
from src.modules.shared import EntityIdVO

_CONNECTOR = "communication_provider_connector"
_MESSAGE_TYPE = "communication_provider_message_type"
_CONNECTION = "communication_provider_connection"
_TEMPLATE = "communication_message_template"
_TEMPLATE_VERSION = "communication_template_version"
_REQUEST = "communication_request"
_OUTBOUND = "communication_outbound_message"
_ATTEMPT = "communication_delivery_attempt"
_EVENT = "communication_delivery_event"


class CommunicationRepository:
    """Runtime-data repository for the communication bounded context."""

    def __init__(
        self,
        *,
        runtime_object_resolver: RuntimeObjectResolverProtocol,
        command_gateway: RuntimeCommandGateway,
        query_gateway: RuntimeQueryGateway,
    ) -> None:
        self._runtime_object_resolver = runtime_object_resolver
        self._command_gateway = command_gateway
        self._query_gateway = query_gateway
        self._descriptors: dict[tuple[UUID, str], RuntimeObjectDescriptor] = {}

    async def upsert_connector(
        self,
        *,
        tenant_id: UUID,
        provider_code: str,
        provider_name: str,
        version: str,
        connector_type: str,
        yaml_spec: dict[str, Any],
        yaml_checksum: str,
        status: str = ConnectorStatus.ACTIVE.value,
    ):
        descriptor = await self._descriptor(tenant_id, _CONNECTOR)
        existing = await self._list(
            tenant_id=tenant_id,
            object_name=_CONNECTOR,
            filters=[
                FilterSpec("provider_code", "eq", provider_code),
                FilterSpec("version", "eq", version),
            ],
            limit=1,
        )
        payload = {
            "provider_code": provider_code,
            "provider_name": provider_name,
            "version": version,
            "connector_type": connector_type,
            "yaml_spec": yaml_spec,
            "yaml_checksum": yaml_checksum,
            "status": status,
        }
        if existing:
            row = await self._command_gateway.update(
                descriptor=descriptor,
                object_id=existing[0]["id"],
                patch=payload,
            )
        else:
            row = await self._command_gateway.insert(
                descriptor=descriptor,
                payload=payload,
            )
        return _connector_model(row)

    async def upsert_message_type(
        self,
        *,
        tenant_id: UUID,
        provider_connector_id: UUID,
        message_type_code: str,
        channel_code: str,
        name: str,
        field_schema: dict[str, Any],
        ui_schema: dict[str, Any],
        is_active: bool = True,
    ):
        descriptor = await self._descriptor(tenant_id, _MESSAGE_TYPE)
        existing = await self._list(
            tenant_id=tenant_id,
            object_name=_MESSAGE_TYPE,
            filters=[
                FilterSpec("provider_connector_id", "eq", provider_connector_id),
                FilterSpec("message_type_code", "eq", message_type_code),
            ],
            limit=1,
        )
        payload = {
            "provider_connector_id": provider_connector_id,
            "message_type_code": message_type_code,
            "channel_code": channel_code,
            "name": name,
            "field_schema": field_schema,
            "ui_schema": ui_schema,
            "is_active": is_active,
        }
        if existing:
            row = await self._command_gateway.update(
                descriptor=descriptor,
                object_id=existing[0]["id"],
                patch=payload,
            )
        else:
            row = await self._command_gateway.insert(
                descriptor=descriptor,
                payload=payload,
            )
        return _message_type_model(row)

    async def get_connector(self, tenant_id: UUID, provider_connector_id: UUID):
        return _optional_model(
            await self._get(tenant_id, _CONNECTOR, provider_connector_id),
            _connector_model,
        )

    async def get_active_connector_by_code(self, tenant_id: UUID, provider_code: str):
        rows = await self._list(
            tenant_id=tenant_id,
            object_name=_CONNECTOR,
            filters=[
                FilterSpec("provider_code", "eq", provider_code),
                FilterSpec("status", "eq", ConnectorStatus.ACTIVE.value),
            ],
            sorting=(SortSpec("created_at", "desc"),),
            limit=1,
        )
        return _optional_model(rows[0] if rows else None, _connector_model)

    async def list_connectors(self, tenant_id: UUID):
        rows = await self._list(
            tenant_id=tenant_id,
            object_name=_CONNECTOR,
            sorting=(SortSpec("provider_code"), SortSpec("version")),
        )
        return [_connector_model(row) for row in rows]

    async def list_message_types(
        self,
        tenant_id: UUID,
        provider_connector_id: UUID | None = None,
    ):
        filters = []
        if provider_connector_id is not None:
            filters.append(
                FilterSpec("provider_connector_id", "eq", provider_connector_id)
            )
        rows = await self._list(
            tenant_id=tenant_id,
            object_name=_MESSAGE_TYPE,
            filters=filters,
            sorting=(SortSpec("channel_code"), SortSpec("message_type_code")),
        )
        return [_message_type_model(row) for row in rows]

    async def get_message_type(self, tenant_id: UUID, provider_message_type_id: UUID):
        return _optional_model(
            await self._get(tenant_id, _MESSAGE_TYPE, provider_message_type_id),
            _message_type_model,
        )

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
    ):
        row = await self._insert(
            tenant_id=tenant_id,
            object_name=_CONNECTION,
            payload={
                "provider_connector_id": provider_connector_id,
                "connection_code": connection_code,
                "connection_name": connection_name,
                "channel_code": channel_code,
                "config": config,
                "secret_ref": secret_ref,
                "secrets_b64": secrets_b64,
                "status": status,
            },
        )
        return _connection_model(tenant_id, row)

    async def list_connections(self, tenant_id: UUID):
        rows = await self._list(
            tenant_id=tenant_id,
            object_name=_CONNECTION,
            sorting=(SortSpec("connection_code"),),
        )
        return [_connection_model(tenant_id, row) for row in rows]

    async def get_connection(self, tenant_id: UUID, provider_connection_id: UUID):
        return _optional_model(
            await self._get(tenant_id, _CONNECTION, provider_connection_id),
            lambda row: _connection_model(tenant_id, row),
        )

    async def find_active_connection(
        self,
        *,
        tenant_id: UUID,
        provider_connector_id: UUID,
        channel_code: str,
    ):
        rows = await self._list(
            tenant_id=tenant_id,
            object_name=_CONNECTION,
            filters=[
                FilterSpec("provider_connector_id", "eq", provider_connector_id),
                FilterSpec("channel_code", "eq", channel_code),
                FilterSpec("status", "eq", ProviderConnectionStatus.ACTIVE.value),
            ],
            sorting=(SortSpec("created_at"),),
            limit=1,
        )
        return _optional_model(
            rows[0] if rows else None,
            lambda row: _connection_model(tenant_id, row),
        )

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
    ):
        row = await self._insert(
            tenant_id=tenant_id,
            object_name=_TEMPLATE,
            payload={
                "template_code": template_code,
                "name": name,
                "description": description,
                "provider_connector_id": provider_connector_id,
                "provider_message_type_id": provider_message_type_id,
                "channel_code": channel_code,
                "message_class": message_class,
                "status": status,
            },
        )
        return _template_model(tenant_id, row)

    async def get_template(self, *, tenant_id: UUID, template_id: UUID):
        return _optional_model(
            await self._get(tenant_id, _TEMPLATE, template_id),
            lambda row: _template_model(tenant_id, row),
        )

    async def get_template_by_code(self, *, tenant_id: UUID, template_code: str):
        rows = await self._list(
            tenant_id=tenant_id,
            object_name=_TEMPLATE,
            filters=[FilterSpec("template_code", "eq", template_code)],
            limit=1,
        )
        return _optional_model(
            rows[0] if rows else None,
            lambda row: _template_model(tenant_id, row),
        )

    async def list_templates(self, tenant_id: UUID):
        rows = await self._list(
            tenant_id=tenant_id,
            object_name=_TEMPLATE,
            sorting=(SortSpec("template_code"),),
        )
        return [_template_model(tenant_id, row) for row in rows]

    async def create_template_version(
        self,
        *,
        tenant_id: UUID,
        template_id: UUID,
        template_payload: dict[str, Any],
        variables_schema: dict[str, Any],
    ):
        version_no = await self._next_template_version_no(tenant_id, template_id)
        row = await self._insert(
            tenant_id=tenant_id,
            object_name=_TEMPLATE_VERSION,
            payload={
                "template_id": template_id,
                "version_no": version_no,
                "template_payload": template_payload,
                "variables_schema": variables_schema,
                "status": TemplateVersionStatus.DRAFT.value,
            },
        )
        return _template_version_model(row)

    async def get_template_version(self, tenant_id: UUID, template_version_id: UUID):
        return _optional_model(
            await self._get(tenant_id, _TEMPLATE_VERSION, template_version_id),
            _template_version_model,
        )

    async def get_active_template_version(self, tenant_id: UUID, template_id: UUID):
        rows = await self._list(
            tenant_id=tenant_id,
            object_name=_TEMPLATE_VERSION,
            filters=[
                FilterSpec("template_id", "eq", template_id),
                FilterSpec("status", "eq", TemplateVersionStatus.ACTIVE.value),
            ],
            limit=1,
        )
        return _optional_model(rows[0] if rows else None, _template_version_model)

    async def activate_template_version(
        self,
        *,
        tenant_id: UUID,
        template,
        version,
        now: datetime,
    ):
        versions = await self._list(
            tenant_id=tenant_id,
            object_name=_TEMPLATE_VERSION,
            filters=[FilterSpec("template_id", "eq", template.template_id)],
        )
        descriptor = await self._descriptor(tenant_id, _TEMPLATE_VERSION)
        for item in versions:
            status = (
                TemplateVersionStatus.ACTIVE.value
                if item["id"] == version.template_version_id
                else (
                    TemplateVersionStatus.DEPRECATED.value
                    if item["status"] == TemplateVersionStatus.ACTIVE.value
                    else item["status"]
                )
            )
            patch: dict[str, Any] = {"status": status}
            if item["id"] == version.template_version_id:
                patch["activated_at"] = now
            await self._command_gateway.update(
                descriptor=descriptor,
                object_id=item["id"],
                patch=patch,
            )
        await self._command_gateway.update(
            descriptor=await self._descriptor(tenant_id, _TEMPLATE),
            object_id=template.template_id,
            patch={"status": TemplateStatus.ACTIVE.value},
        )
        fresh = await self._get(
            tenant_id, _TEMPLATE_VERSION, version.template_version_id
        )
        return _template_version_model(fresh)

    async def get_existing_send_by_idempotency(
        self,
        *,
        tenant_id: UUID,
        idempotency_key: str,
    ):
        requests = await self._list(
            tenant_id=tenant_id,
            object_name=_REQUEST,
            filters=[FilterSpec("idempotency_key", "eq", idempotency_key)],
            limit=1,
        )
        if not requests:
            return None
        outbounds = await self._list(
            tenant_id=tenant_id,
            object_name=_OUTBOUND,
            filters=[FilterSpec("communication_request_id", "eq", requests[0]["id"])],
            limit=1,
        )
        if not outbounds:
            return None
        return _request_model(tenant_id, requests[0]), _outbound_model(
            tenant_id, outbounds[0]
        )

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
    ):
        request = await self._insert(
            tenant_id=tenant_id,
            object_name=_REQUEST,
            payload={
                "initiator_type": initiator_type,
                "initiator_ref_id": initiator_ref_id,
                "correlation_id": correlation_id,
                "idempotency_key": idempotency_key,
                "message_class": message_class,
                "channel_code": channel_code,
                "template_id": template_id,
                "template_version_id": template_version_id,
                "contact_id": contact_id,
                "recipient_address": recipient_address,
                "recipient_snapshot": recipient_snapshot,
                "variables": variables,
                "scheduled_at": scheduled_at,
                "priority": priority,
                "status": RequestStatus.QUEUED.value,
            },
        )
        outbound = await self._insert(
            tenant_id=tenant_id,
            object_name=_OUTBOUND,
            payload={
                "communication_request_id": request["id"],
                "provider_connection_id": provider_connection_id,
                "channel_code": channel_code,
                "message_class": message_class,
                "priority": priority,
                "contact_id": contact_id,
                "recipient_address": recipient_address,
                "rendered_payload": {},
                "provider_request_payload": {},
                "internal_status": OutboundMessageStatus.QUEUED.value,
                "queued_at": now,
            },
        )
        return _request_model(tenant_id, request), _outbound_model(tenant_id, outbound)

    async def claim_queued_messages(self, tenant_id: UUID, limit: int):
        claimed = []
        for _ in range(limit):
            token = uuid4()
            rows = await self._claim_outbounds(
                tenant_id=tenant_id,
                filters=[
                    FilterSpec(
                        "internal_status", "eq", OutboundMessageStatus.QUEUED.value
                    )
                ],
                patch={
                    "internal_status": OutboundMessageStatus.SENDING.value,
                    "processing_token": token,
                    "processing_started_at": utc_now(),
                    "processing_deadline_at": utc_now() + timedelta(seconds=300),
                },
                limit=1,
            )
            if not rows:
                break
            claimed.append(_outbound_model(tenant_id, rows[0]))
        return claimed

    async def list_publishable_outbounds(
        self,
        *,
        tenant_id: UUID,
        limit: int,
        now: datetime,
        republish_before: datetime,
    ):
        rows = await self._list(
            tenant_id=tenant_id,
            object_name=_OUTBOUND,
            filters=[
                FilterSpec("internal_status", "eq", OutboundMessageStatus.QUEUED.value),
                FilterGroupSpec(
                    "or",
                    (
                        FilterSpec("next_attempt_at", "eq", None),
                        FilterSpec("next_attempt_at", "lte", now),
                    ),
                ),
                FilterGroupSpec(
                    "or",
                    (
                        FilterSpec("queue_published_at", "eq", None),
                        FilterSpec("queue_published_at", "lte", republish_before),
                    ),
                ),
            ],
            sorting=(SortSpec("priority"), SortSpec("created_at")),
            limit=limit,
        )
        return [_outbound_model(tenant_id, row) for row in rows]

    async def mark_outbound_published(
        self,
        *,
        tenant_id: UUID,
        outbound_message_id: UUID,
        published_at: datetime,
    ) -> None:
        outbound = await self.get_outbound_by_id(tenant_id, outbound_message_id)
        if outbound is None:
            return
        await self._command_gateway.update(
            descriptor=await self._descriptor(tenant_id, _OUTBOUND),
            object_id=outbound_message_id,
            patch={
                "queue_published_at": published_at,
                "queue_publish_count": int(outbound.queue_publish_count or 0) + 1,
            },
        )

    async def get_outbound_by_id(self, tenant_id: UUID, outbound_message_id: UUID):
        return _optional_model(
            await self._get(tenant_id, _OUTBOUND, outbound_message_id),
            lambda row: _outbound_model(tenant_id, row),
        )

    async def claim_outbound_for_processing(
        self,
        *,
        tenant_id: UUID,
        outbound_message_id: UUID,
        processing_token: UUID,
        now: datetime,
        lease_until: datetime,
    ):
        rows = await self._claim_outbounds(
            tenant_id=tenant_id,
            filters=[
                FilterSpec("id", "eq", outbound_message_id),
                FilterSpec("internal_status", "eq", OutboundMessageStatus.QUEUED.value),
                FilterGroupSpec(
                    "or",
                    (
                        FilterSpec("next_attempt_at", "eq", None),
                        FilterSpec("next_attempt_at", "lte", now),
                    ),
                ),
            ],
            patch={
                "internal_status": OutboundMessageStatus.SENDING.value,
                "processing_token": processing_token,
                "processing_started_at": now,
                "processing_deadline_at": lease_until,
            },
            limit=1,
        )
        return _optional_model(
            rows[0] if rows else None, lambda row: _outbound_model(tenant_id, row)
        )

    async def load_processing_context(self, tenant_id: UUID, outbound_message_id: UUID):
        outbound = await self.get_outbound_by_id(tenant_id, outbound_message_id)
        request = _request_model(
            tenant_id,
            await self._required(
                _REQUEST,
                await self._get(tenant_id, _REQUEST, outbound.communication_request_id),
            ),
        )
        template = _template_model(
            tenant_id,
            await self._required(
                _TEMPLATE, await self._get(tenant_id, _TEMPLATE, request.template_id)
            ),
        )
        version = _template_version_model(
            await self._required(
                _TEMPLATE_VERSION,
                await self._get(
                    tenant_id, _TEMPLATE_VERSION, request.template_version_id
                ),
            )
        )
        connection = _connection_model(
            tenant_id,
            await self._required(
                _CONNECTION,
                await self._get(
                    tenant_id, _CONNECTION, outbound.provider_connection_id
                ),
            ),
        )
        connector = _connector_model(
            await self._required(
                _CONNECTOR,
                await self._get(
                    tenant_id, _CONNECTOR, connection.provider_connector_id
                ),
            )
        )
        message_type = _message_type_model(
            await self._required(
                _MESSAGE_TYPE,
                await self._get(
                    tenant_id, _MESSAGE_TYPE, template.provider_message_type_id
                ),
            )
        )
        return outbound, request, template, version, connection, connector, message_type

    async def create_delivery_attempt(
        self,
        *,
        tenant_id: UUID,
        outbound_message_id: UUID,
        provider_connection_id: UUID,
        request_payload: dict[str, Any],
    ):
        attempt_no = await self._next_attempt_no(tenant_id, outbound_message_id)
        row = await self._insert(
            tenant_id=tenant_id,
            object_name=_ATTEMPT,
            payload={
                "outbound_message_id": outbound_message_id,
                "provider_connection_id": provider_connection_id,
                "attempt_no": attempt_no,
                "status": AttemptStatus.STARTED.value,
                "request_payload": request_payload,
            },
        )
        return _attempt_model(row)

    async def complete_outbound_processing(
        self,
        *,
        tenant_id: UUID,
        outbound_message_id: UUID,
        processing_token: UUID,
        delivery_attempt_id: UUID,
        rendered_payload: dict[str, Any],
        provider_request_payload: dict[str, Any],
        response_payload: dict[str, Any],
        http_status_code: int | None,
        external_message_id: str | None,
        external_status: str | None,
        internal_status: str,
        finished_at: datetime,
    ) -> bool:
        outbound = await self.get_outbound_by_id(tenant_id, outbound_message_id)
        if outbound is None or outbound.processing_token != processing_token:
            return False
        patch = {
            "rendered_payload": rendered_payload,
            "provider_request_payload": provider_request_payload,
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
        updated = await self._command_gateway.update_where(
            descriptor=await self._descriptor(tenant_id, _OUTBOUND),
            filters=[
                FilterSpec("id", "eq", outbound_message_id),
                FilterSpec("processing_token", "eq", processing_token),
            ],
            patch=patch,
        )
        if not updated:
            return False
        await self._command_gateway.update(
            descriptor=await self._descriptor(tenant_id, _REQUEST),
            object_id=outbound.communication_request_id,
            patch={"status": _request_status_for_internal_status(internal_status)},
        )
        await self._command_gateway.update(
            descriptor=await self._descriptor(tenant_id, _ATTEMPT),
            object_id=delivery_attempt_id,
            patch={
                "status": AttemptStatus.SUCCESS.value,
                "response_payload": response_payload,
                "http_status_code": http_status_code,
                "external_message_id": external_message_id,
                "finished_at": finished_at,
            },
        )
        return True

    async def fail_outbound_processing(
        self,
        *,
        tenant_id: UUID,
        outbound_message_id: UUID,
        processing_token: UUID,
        delivery_attempt_id: UUID | None,
        error_code: str,
        error_message: str,
        finished_at: datetime,
        response_payload: dict[str, Any] | None = None,
        http_status_code: int | None = None,
        external_message_id: str | None = None,
        external_status: str | None = None,
        retry_at: datetime | None = None,
    ) -> bool:
        outbound = await self.get_outbound_by_id(tenant_id, outbound_message_id)
        if outbound is None or outbound.processing_token != processing_token:
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
        updated = await self._command_gateway.update_where(
            descriptor=await self._descriptor(tenant_id, _OUTBOUND),
            filters=[
                FilterSpec("id", "eq", outbound_message_id),
                FilterSpec("processing_token", "eq", processing_token),
            ],
            patch=outbound_patch,
        )
        if not updated:
            return False
        await self._command_gateway.update(
            descriptor=await self._descriptor(tenant_id, _REQUEST),
            object_id=outbound.communication_request_id,
            patch={
                "status": (
                    RequestStatus.QUEUED.value
                    if retryable
                    else RequestStatus.FAILED.value
                )
            },
        )
        if delivery_attempt_id is not None:
            await self._command_gateway.update(
                descriptor=await self._descriptor(tenant_id, _ATTEMPT),
                object_id=delivery_attempt_id,
                patch={
                    "status": (
                        AttemptStatus.RETRYABLE_FAILED.value
                        if retryable
                        else AttemptStatus.NON_RETRYABLE_FAILED.value
                    ),
                    "response_payload": response_payload or {"error": error_message},
                    "http_status_code": http_status_code,
                    "external_message_id": external_message_id,
                    "error_code": error_code,
                    "error_message": error_message,
                    "finished_at": finished_at,
                },
            )
        return True

    async def recover_stuck_outbounds(
        self,
        *,
        tenant_id: UUID,
        older_than: datetime,
        now: datetime,
        limit: int,
    ) -> int:
        rows = await self._claim_outbounds(
            tenant_id=tenant_id,
            filters=[
                FilterSpec(
                    "internal_status", "eq", OutboundMessageStatus.SENDING.value
                ),
                FilterGroupSpec(
                    "or",
                    (
                        FilterSpec("processing_deadline_at", "lte", now),
                        FilterSpec("processing_started_at", "lte", older_than),
                    ),
                ),
            ],
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
            await self._command_gateway.update(
                descriptor=await self._descriptor(tenant_id, _REQUEST),
                object_id=row["communication_request_id"],
                patch={"status": RequestStatus.FAILED.value},
            )
        return len(rows)

    async def get_outbound(self, *, tenant_id: UUID, outbound_message_id: UUID):
        return await self.get_outbound_by_id(tenant_id, outbound_message_id)

    async def list_outbound(self, *, tenant_id: UUID, limit: int, offset: int):
        rows = await self._list(
            tenant_id=tenant_id,
            object_name=_OUTBOUND,
            sorting=(SortSpec("created_at", "desc"),),
            limit=limit,
            offset=offset,
        )
        return [_outbound_model(tenant_id, row) for row in rows]

    async def find_outbound_by_external_message_id(
        self,
        *,
        tenant_id: UUID,
        external_message_id: str,
    ):
        rows = await self._list(
            tenant_id=tenant_id,
            object_name=_OUTBOUND,
            filters=[FilterSpec("external_message_id", "eq", external_message_id)],
            sorting=(SortSpec("created_at", "desc"),),
            limit=1,
        )
        return _optional_model(
            rows[0] if rows else None, lambda row: _outbound_model(tenant_id, row)
        )

    async def add_delivery_event(
        self,
        *,
        tenant_id: UUID,
        outbound_message_id: UUID | None,
        provider_connection_id: UUID | None,
        external_message_id: str | None,
        external_status: str | None,
        internal_status: str,
        event_type: str,
        event_at: datetime | None,
        raw_payload: dict[str, Any],
    ):
        row = await self._insert(
            tenant_id=tenant_id,
            object_name=_EVENT,
            payload={
                "outbound_message_id": outbound_message_id,
                "provider_connection_id": provider_connection_id,
                "external_message_id": external_message_id,
                "external_status": external_status,
                "internal_status": internal_status,
                "event_type": event_type,
                "event_at": event_at,
                "raw_payload": raw_payload,
            },
        )
        return _event_model(tenant_id, row)

    async def update_outbound_status_from_event(
        self,
        *,
        tenant_id: UUID,
        outbound_message_id: UUID,
        external_status: str | None,
        internal_status: str,
        now: datetime,
    ) -> None:
        outbound = await self.get_outbound_by_id(tenant_id, outbound_message_id)
        if outbound is None:
            return
        await self._command_gateway.update(
            descriptor=await self._descriptor(tenant_id, _OUTBOUND),
            object_id=outbound_message_id,
            patch={
                "external_status": external_status,
                "internal_status": internal_status,
                **_status_timestamp_patch(outbound, internal_status, now),
            },
        )

    async def _next_template_version_no(
        self, tenant_id: UUID, template_id: UUID
    ) -> int:
        rows = await self._list(
            tenant_id=tenant_id,
            object_name=_TEMPLATE_VERSION,
            filters=[FilterSpec("template_id", "eq", template_id)],
            sorting=(SortSpec("version_no", "desc"),),
            limit=1,
        )
        return int(rows[0]["version_no"] if rows else 0) + 1

    async def _next_attempt_no(self, tenant_id: UUID, outbound_message_id: UUID) -> int:
        rows = await self._list(
            tenant_id=tenant_id,
            object_name=_ATTEMPT,
            filters=[FilterSpec("outbound_message_id", "eq", outbound_message_id)],
            sorting=(SortSpec("attempt_no", "desc"),),
            limit=1,
        )
        return int(rows[0]["attempt_no"] if rows else 0) + 1

    async def _insert(
        self,
        *,
        tenant_id: UUID,
        object_name: str,
        payload: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        return await self._command_gateway.insert(
            descriptor=await self._descriptor(tenant_id, object_name),
            payload=payload,
        )

    async def _get(
        self,
        tenant_id: UUID,
        object_name: str,
        object_id: UUID,
    ) -> Mapping[str, Any] | None:
        return await self._query_gateway.get_by_id(
            descriptor=await self._descriptor(tenant_id, object_name),
            object_id=object_id,
        )

    async def _list(
        self,
        *,
        tenant_id: UUID,
        object_name: str,
        filters=(),
        sorting=(),
        limit: int | None = None,
        offset: int = 0,
    ) -> list[Mapping[str, Any]]:
        return await self._query_gateway.list(
            descriptor=await self._descriptor(tenant_id, object_name),
            filters=filters,
            sorting=sorting,
            page=PageSpec(limit=limit, offset=offset) if limit is not None else None,
        )

    async def _claim_outbounds(
        self,
        *,
        tenant_id: UUID,
        filters,
        patch: Mapping[str, Any],
        limit: int,
    ) -> list[Mapping[str, Any]]:
        return await self._command_gateway.claim(
            descriptor=await self._descriptor(tenant_id, _OUTBOUND),
            filters=filters,
            patch=patch,
            sorting=(SortSpec("priority"), SortSpec("created_at")),
            limit=limit,
        )

    async def _descriptor(
        self,
        tenant_id: UUID,
        object_name: str,
    ) -> RuntimeObjectDescriptor:
        key = (tenant_id, object_name)
        descriptor = self._descriptors.get(key)
        if descriptor is None:
            descriptor = await self._runtime_object_resolver.resolve(
                EntityIdVO.from_value(tenant_id),
                object_name,
            )
            self._descriptors[key] = descriptor
        return descriptor

    @staticmethod
    async def _required(label: str, row: Mapping[str, Any] | None) -> Mapping[str, Any]:
        if row is None:
            raise LookupError(
                f"Required communication runtime row '{label}' was not found."
            )
        return row


def utc_now() -> datetime:
    return datetime.now(UTC)


def connector_to_dto(model) -> ProviderConnectorDTO:
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


def message_type_to_dto(model) -> ProviderMessageTypeDTO:
    return ProviderMessageTypeDTO(
        provider_message_type_id=model.provider_message_type_id,
        provider_connector_id=model.provider_connector_id,
        message_type_code=model.message_type_code,
        channel_code=model.channel_code,
        name=model.name,
        field_schema=dict(model.field_schema or {}),
        ui_schema=dict(model.ui_schema or {}),
        is_active=bool(model.is_active),
    )


def connection_to_dto(model) -> ProviderConnectionDTO:
    return ProviderConnectionDTO(
        provider_connection_id=model.provider_connection_id,
        tenant_id=model.tenant_id,
        provider_connector_id=model.provider_connector_id,
        connection_code=model.connection_code,
        connection_name=model.connection_name,
        channel_code=model.channel_code,
        config=dict(model.config or {}),
        secret_ref=model.secret_ref,
        has_secrets=bool(model.secrets_b64),
        status=model.status,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def template_to_dto(model, active_version=None) -> MessageTemplateDTO:
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


def template_version_to_dto(model) -> TemplateVersionDTO:
    return TemplateVersionDTO(
        template_version_id=model.template_version_id,
        template_id=model.template_id,
        version_no=model.version_no,
        template_payload=dict(model.template_payload or {}),
        variables_schema=dict(model.variables_schema or {}),
        status=model.status,
        created_at=model.created_at,
        activated_at=model.activated_at,
    )


def outbound_to_dto(model) -> OutboundMessageDTO:
    return OutboundMessageDTO(
        outbound_message_id=model.outbound_message_id,
        tenant_id=model.tenant_id,
        communication_request_id=model.communication_request_id,
        provider_connection_id=model.provider_connection_id,
        channel_code=model.channel_code,
        contact_id=model.contact_id,
        recipient_address=model.recipient_address,
        rendered_payload=dict(model.rendered_payload or {}),
        provider_request_payload=dict(model.provider_request_payload or {}),
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


def _connector_model(row: Mapping[str, Any]):
    return _model(row, provider_connector_id=row["id"])


def _message_type_model(row: Mapping[str, Any]):
    return _model(row, provider_message_type_id=row["id"])


def _connection_model(tenant_id: UUID, row: Mapping[str, Any]):
    return _model(row, tenant_id=tenant_id, provider_connection_id=row["id"])


def _template_model(tenant_id: UUID, row: Mapping[str, Any]):
    return _model(row, tenant_id=tenant_id, template_id=row["id"])


def _template_version_model(row: Mapping[str, Any]):
    return _model(row, template_version_id=row["id"])


def _request_model(tenant_id: UUID, row: Mapping[str, Any]):
    return _model(row, tenant_id=tenant_id, communication_request_id=row["id"])


def _outbound_model(tenant_id: UUID, row: Mapping[str, Any]):
    return _model(row, tenant_id=tenant_id, outbound_message_id=row["id"])


def _attempt_model(row: Mapping[str, Any]):
    return _model(row, delivery_attempt_id=row["id"])


def _event_model(tenant_id: UUID, row: Mapping[str, Any]):
    return _model(row, tenant_id=tenant_id, delivery_event_id=row["id"])


def _model(row: Mapping[str, Any], **aliases: Any):
    values = dict(row)
    values.update(aliases)
    return SimpleNamespace(**values)


def _optional_model(row: Mapping[str, Any] | None, factory):
    return None if row is None else factory(row)


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
    outbound, internal_status: str, now: datetime
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


__all__ = [
    "CommunicationRepository",
    "connection_to_dto",
    "connector_to_dto",
    "message_type_to_dto",
    "outbound_to_dto",
    "template_to_dto",
    "template_version_to_dto",
    "utc_now",
]
