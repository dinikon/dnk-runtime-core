from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from uuid import uuid4

from fastapi import HTTPException
from pydantic import ValidationError

from src.modules.communication.application.outbound_message.dto import (
    SendCommunicationResultDTO,
)
from src.modules.communication.application.delivery import (
    DeliveryAttemptDTO,
    DeliveryEventDTO,
)
from src.modules.communication.application.provider_connection import (
    ProviderConnectionDTO,
)
from src.modules.communication.application.provider_connector import (
    ProviderConnectorDTO,
)
from src.modules.communication.domain.error import (
    CommunicationValidationError,
)
from src.modules.communication.domain.outbound_message import (
    OutboundMessageStatus,
)
from src.modules.communication.domain.delivery import DeliveryEventIdVO
from src.modules.communication.domain.provider_connector import (
    ProviderConnectorCodeVO,
    ProviderConnectorIdVO,
    ProviderConnectorNotFoundError,
)
from src.modules.communication.domain.provider_connection import (
    ProviderConnectionIdVO,
)
from src.modules.communication.presentation.http.outbound_message.controller.list_messages import (
    list_messages,
)
from src.modules.communication.presentation.http.outbound_message.controller.publish_send_job_after_commit import (
    publish_send_job_after_commit,
)
from src.modules.communication.presentation.http.outbound_message.requests import (
    SendCommunicationRequestSchema,
)
from src.modules.communication.presentation.http.provider_connection.controller.create_provider_connection import (
    create_provider_connection,
)
from src.modules.communication.presentation.http.provider_connection.controller.delete_provider_connection import (
    delete_provider_connection,
)
from src.modules.communication.presentation.http.provider_connection.controller.update_provider_connection_status import (
    update_provider_connection_status,
)
from src.modules.communication.presentation.http.provider_connection.requests import (
    CreateProviderConnectionRequestSchema,
    UpdateProviderConnectionStatusRequestSchema,
)
from src.modules.communication.presentation.http.provider_connector.controller.delete_provider_connector import (
    delete_provider_connector,
)
from src.modules.communication.presentation.http.provider_connector.controller.update_provider_connector_status import (
    update_provider_connector_status,
)
from src.modules.communication.presentation.http.provider_connector.requests import (
    UpdateProviderConnectorStatusRequestSchema,
)
from src.modules.communication.presentation.http.message_template.controller.create_message_template import (
    create_message_template,
)
from src.modules.communication.presentation.http.message_template.requests import (
    CreateMessageTemplateRequestSchema,
)
from src.modules.communication.presentation.http.router import router
from src.modules.communication.presentation.http.delivery.controller.handle_provider_webhook import (
    handle_provider_webhook,
)
from src.modules.communication.presentation.http.delivery.controller.list_delivery_attempts import (
    list_delivery_attempts,
)
from src.modules.communication.presentation.http.delivery.controller.list_message_delivery_attempts import (
    list_message_delivery_attempts,
)
from src.modules.communication.presentation.http.delivery.controller.list_delivery_events import (
    list_delivery_events,
)
from src.modules.communication.presentation.http.delivery.controller.list_message_delivery_events import (
    list_message_delivery_events,
)
from src.modules.communication.presentation.http.delivery.requests import (
    ListDeliveryAttemptsRequestSchema,
    ListDeliveryEventsRequestSchema,
    ListMessageDeliveryAttemptsRequestSchema,
    ListMessageDeliveryEventsRequestSchema,
)
from src.modules.runtime_data.domain.error import RuntimeDataPersistenceError
from src.modules.shared import EntityIdVO


class CommunicationHttpRouterTests(unittest.TestCase):
    def test_router_exposes_mvp_routes(self) -> None:
        routes = {
            (method, route.path)
            for route in router.routes
            for method in route.methods or set()
        }

        self.assertIn(
            ("POST", "/communication/providers/connectors/import-yaml"), routes
        )
        self.assertIn(("GET", "/communication/providers/connectors"), routes)
        self.assertIn(
            (
                "PATCH",
                "/communication/providers/connectors/{provider_connector_id}/status",
            ),
            routes,
        )
        self.assertIn(
            ("DELETE", "/communication/providers/connectors/{provider_connector_id}"),
            routes,
        )
        self.assertIn(("POST", "/communication/providers/connections"), routes)
        self.assertIn(("GET", "/communication/providers/connections"), routes)
        self.assertIn(
            (
                "PATCH",
                "/communication/providers/connections/{provider_connection_id}/status",
            ),
            routes,
        )
        self.assertIn(
            (
                "DELETE",
                "/communication/providers/connections/{provider_connection_id}",
            ),
            routes,
        )
        self.assertIn(("POST", "/communication/templates"), routes)
        self.assertIn(
            ("POST", "/communication/templates/{template_id}/versions"), routes
        )
        self.assertIn(
            (
                "POST",
                "/communication/templates/{template_id}/versions/{version_id}/activate",
            ),
            routes,
        )
        self.assertIn(("GET", "/communication/templates"), routes)
        self.assertIn(("POST", "/communication/send"), routes)
        self.assertIn(("GET", "/communication/messages"), routes)
        self.assertIn(("GET", "/communication/messages/{outbound_message_id}"), routes)
        self.assertIn(
            ("GET", "/communication/messages/{outbound_message_id}/attempts"),
            routes,
        )
        self.assertIn(
            ("GET", "/communication/messages/{outbound_message_id}/events"),
            routes,
        )
        self.assertIn(("GET", "/communication/delivery-attempts"), routes)
        self.assertIn(("GET", "/communication/delivery-events"), routes)
        self.assertIn(
            ("POST", "/communication/webhooks/{tenant_id}/{provider_code}"),
            routes,
        )

    def test_send_request_requires_generic_resolved_recipient_fields(self) -> None:
        template_id = uuid4()
        correlation_id = uuid4()

        payload = SendCommunicationRequestSchema(
            initiator_type="CRM",
            initiator_ref_id="manual:1",
            correlation_id=correlation_id,
            idempotency_key="idem-1",
            channel_code="SMS",
            template_id=template_id,
            recipient_identifier_type="PHONE",
            recipient_address="+380501111111",
            recipient_snapshot={"source_kind": "RAW_VALUE"},
        )

        self.assertEqual(payload.template_id, template_id)
        self.assertEqual(payload.correlation_id, correlation_id)
        self.assertEqual(payload.recipient_identifier_type, "PHONE")

    def test_send_request_rejects_source_specific_contact_id(self) -> None:
        with self.assertRaises(ValidationError):
            SendCommunicationRequestSchema(
                initiator_type="CRM",
                initiator_ref_id="manual:1",
                correlation_id=uuid4(),
                idempotency_key="idem-1",
                channel_code="SMS",
                template_id=uuid4(),
                recipient_identifier_type="PHONE",
                recipient_address="+380501111111",
                recipient_snapshot={"source_kind": "RAW_VALUE"},
                contact_id=uuid4(),
            )


class _PublisherStub:
    def __init__(self) -> None:
        self.published: list[tuple[str, str, str]] = []

    async def publish(
        self,
        *,
        tenant_id,
        outbound_message_id,
        source,
        published_at,
    ) -> None:
        self.published.append((str(tenant_id), str(outbound_message_id), source))


class _RepositoryStub:
    def __init__(self) -> None:
        self.marked: list[tuple[str, datetime]] = []

    async def mark_outbound_published(
        self,
        *,
        tenant_id,
        outbound_message_id,
        published_at,
    ) -> None:
        self.marked.append((str(tenant_id), str(outbound_message_id), published_at))


class _UnitOfWorkStub:
    def __init__(self) -> None:
        self.commits = 0
        self.rollbacks = 0

    async def commit(self) -> None:
        self.commits += 1

    async def rollback(self) -> None:
        self.rollbacks += 1


class _FailingUseCase:
    def __init__(self, exc: Exception) -> None:
        self.exc = exc

    async def __call__(self, *args, **kwargs):
        raise self.exc


class _CreateProviderConnectionUseCase:
    def __init__(self) -> None:
        self.command = None

    async def __call__(self, command):
        self.command = command
        now = datetime(2026, 5, 13, 12, 0, tzinfo=UTC)
        return ProviderConnectionDTO(
            provider_connection_id=command.provider_connection_id.uuid,
            tenant_id=command.tenant_id.uuid,
            provider_connector_id=command.provider_connector_id.uuid,
            connection_code=command.connection_code,
            connection_name=command.connection_name,
            channel_code=command.channel_code,
            config=command.config,
            secret_ref=command.secret_ref,
            has_secrets=bool(command.secrets),
            status="ACTIVE",
            created_at=now,
            updated_at=now,
        )


class _UpdateProviderConnectionStatusUseCase:
    def __init__(self) -> None:
        self.command = None

    async def __call__(self, command):
        self.command = command
        now = datetime(2026, 5, 13, 12, 0, tzinfo=UTC)
        return ProviderConnectionDTO(
            provider_connection_id=command.provider_connection_id.uuid,
            tenant_id=command.tenant_id.uuid,
            provider_connector_id=uuid4(),
            connection_code="gms",
            connection_name="GMS",
            channel_code="SMS",
            config={},
            secret_ref=None,
            has_secrets=False,
            status=command.status,
            created_at=now,
            updated_at=now,
        )


class _UpdateProviderConnectorStatusUseCase:
    def __init__(self) -> None:
        self.command = None

    async def __call__(self, command):
        self.command = command
        now = datetime(2026, 5, 13, 12, 0, tzinfo=UTC)
        return ProviderConnectorDTO(
            provider_connector_id=command.provider_connector_id.uuid,
            provider_code="gms",
            provider_name="GMS",
            version="1.0",
            connector_type="YAML_HTTP",
            channels=["SMS"],
            config_schema={},
            secrets_schema={},
            status=command.status,
            created_at=now,
            updated_at=now,
        )


class _HandleProviderWebhookUseCase:
    def __init__(self) -> None:
        self.command = None

    async def __call__(self, command):
        self.command = command
        return SimpleNamespace(
            accepted=True,
            matched=True,
            outbound_message_id=uuid4(),
            internal_status="DELIVERED",
        )


class _ListDeliveryAttemptsUseCase:
    def __init__(self) -> None:
        self.query = None
        self.now = datetime(2026, 5, 14, 12, 0, tzinfo=UTC)

    async def __call__(self, query):
        self.query = query
        return [
            DeliveryAttemptDTO(
                delivery_attempt_id=uuid4(),
                tenant_id=query.tenant_id.uuid,
                outbound_message_id=query.outbound_message_id.uuid,
                provider_connection_id=uuid4(),
                attempt_no=1,
                status="SUCCESS",
                request_payload={"body": "hello"},
                response_payload={"status": "sent"},
                http_status_code=200,
                external_message_id="ext-1",
                error_code=None,
                error_message=None,
                started_at=self.now,
                finished_at=self.now,
            )
        ]


class _ListDeliveryEventsUseCase:
    def __init__(self) -> None:
        self.query = None
        self.now = datetime(2026, 5, 14, 12, 0, tzinfo=UTC)

    async def __call__(self, query):
        self.query = query
        return [
            DeliveryEventDTO(
                delivery_event_id=uuid4(),
                tenant_id=query.tenant_id.uuid,
                outbound_message_id=(
                    None
                    if query.outbound_message_id is None
                    else query.outbound_message_id.uuid
                ),
                provider_connection_id=uuid4(),
                external_message_id="ext-1",
                external_status="Delivered",
                internal_status="DELIVERED",
                event_type="WEBHOOK_RECEIVED",
                event_at=self.now,
                raw_payload={"message_id": "ext-1"},
                created_at=self.now,
            )
        ]


def _context():
    return SimpleNamespace(principal=SimpleNamespace(tenant_id=uuid4()))


class CommunicationControllerErrorTests(unittest.IsolatedAsyncioTestCase):

    async def test_create_provider_connection_generates_id_and_converts_command_vo(
        self,
    ) -> None:
        tenant_id = uuid4()
        provider_connection_id = uuid4()
        provider_connector_id = uuid4()
        use_case = _CreateProviderConnectionUseCase()

        with patch(
            "src.modules.communication.presentation.http.provider_connection.controller.create_provider_connection.uuid6.uuid7",
            return_value=provider_connection_id,
        ):
            response = await create_provider_connection(
                payload=CreateProviderConnectionRequestSchema(
                    provider_connector_id=provider_connector_id,
                    connection_code="gms",
                    connection_name="GMS",
                    channel_code="SMS",
                    config={"client_id": "abc"},
                    secrets={"token": "secret"},
                ),
                context=SimpleNamespace(principal=SimpleNamespace(tenant_id=tenant_id)),
                use_case=use_case,
            )

        self.assertEqual(response.provider_connection_id, provider_connection_id)
        self.assertEqual(response.tenant_id, tenant_id)
        self.assertIs(type(use_case.command.tenant_id), EntityIdVO)
        self.assertIs(
            type(use_case.command.provider_connection_id),
            ProviderConnectionIdVO,
        )
        self.assertIs(
            type(use_case.command.provider_connector_id),
            ProviderConnectorIdVO,
        )

    async def test_update_provider_connection_status_maps_command_and_response(
        self,
    ) -> None:
        tenant_id = uuid4()
        provider_connection_id = uuid4()
        use_case = _UpdateProviderConnectionStatusUseCase()

        response = await update_provider_connection_status(
            provider_connection_id=provider_connection_id,
            payload=UpdateProviderConnectionStatusRequestSchema(status="DISABLED"),
            context=SimpleNamespace(principal=SimpleNamespace(tenant_id=tenant_id)),
            use_case=use_case,
        )

        self.assertEqual(response.provider_connection_id, provider_connection_id)
        self.assertEqual(response.tenant_id, tenant_id)
        self.assertEqual(response.status, "DISABLED")
        self.assertIs(type(use_case.command.tenant_id), EntityIdVO)
        self.assertIs(
            type(use_case.command.provider_connection_id),
            ProviderConnectionIdVO,
        )
        self.assertEqual(use_case.command.status, "DISABLED")

    async def test_update_provider_connector_status_maps_validation_to_422(
        self,
    ) -> None:
        with self.assertRaises(HTTPException) as caught:
            await update_provider_connector_status(
                provider_connector_id=uuid4(),
                payload=UpdateProviderConnectorStatusRequestSchema(status="DISABLED"),
                context=_context(),
                use_case=_FailingUseCase(
                    CommunicationValidationError(
                        "Provider connector status transition is not allowed."
                    )
                ),
            )

        self.assertEqual(caught.exception.status_code, 422)
        self.assertEqual(
            caught.exception.detail,
            "Provider connector status transition is not allowed.",
        )

    async def test_update_provider_connector_status_maps_command_and_response(
        self,
    ) -> None:
        tenant_id = uuid4()
        provider_connector_id = uuid4()
        use_case = _UpdateProviderConnectorStatusUseCase()

        response = await update_provider_connector_status(
            provider_connector_id=provider_connector_id,
            payload=UpdateProviderConnectorStatusRequestSchema(status="ACTIVE"),
            context=SimpleNamespace(principal=SimpleNamespace(tenant_id=tenant_id)),
            use_case=use_case,
        )

        self.assertEqual(response.provider_connector_id, provider_connector_id)
        self.assertEqual(response.status, "ACTIVE")
        self.assertEqual(response.channels, ["SMS"])
        self.assertIs(type(use_case.command.tenant_id), EntityIdVO)
        self.assertIs(
            type(use_case.command.provider_connector_id),
            ProviderConnectorIdVO,
        )
        self.assertEqual(use_case.command.status, "ACTIVE")

    async def test_delete_provider_connection_maps_runtime_conflict_to_409(
        self,
    ) -> None:
        with self.assertRaises(HTTPException) as caught:
            await delete_provider_connection(
                provider_connection_id=uuid4(),
                context=_context(),
                use_case=_FailingUseCase(RuntimeDataPersistenceError("db failed")),
            )

        self.assertEqual(caught.exception.status_code, 409)
        self.assertEqual(caught.exception.detail, "db failed")

    async def test_delete_provider_connector_maps_not_found_to_404(self) -> None:
        with self.assertRaises(HTTPException) as caught:
            await delete_provider_connector(
                provider_connector_id=uuid4(),
                context=_context(),
                use_case=_FailingUseCase(ProviderConnectorNotFoundError()),
            )

        self.assertEqual(caught.exception.status_code, 404)
        self.assertEqual(
            caught.exception.detail,
            "Provider connector was not found.",
        )

    async def test_handle_provider_webhook_generates_id_and_converts_command_vo(
        self,
    ) -> None:
        tenant_id = uuid4()
        delivery_event_id = uuid4()
        use_case = _HandleProviderWebhookUseCase()

        with patch(
            "src.modules.communication.presentation.http.delivery.controller.handle_provider_webhook.uuid6.uuid7",
            return_value=delivery_event_id,
        ):
            response = await handle_provider_webhook(
                tenant_id=tenant_id,
                provider_code="gms",
                raw_payload={"message_id": "ext-1"},
                _context=None,
                use_case=use_case,
            )

        self.assertTrue(response.accepted)
        self.assertTrue(response.matched)
        self.assertIs(type(use_case.command.tenant_id), EntityIdVO)
        self.assertEqual(use_case.command.tenant_id.uuid, tenant_id)
        self.assertIs(
            type(use_case.command.delivery_event_id),
            DeliveryEventIdVO,
        )
        self.assertEqual(use_case.command.delivery_event_id.uuid, delivery_event_id)
        self.assertIs(
            type(use_case.command.provider_code),
            ProviderConnectorCodeVO,
        )

    async def test_list_message_delivery_attempts_maps_path_filter_and_payload(
        self,
    ) -> None:
        tenant_id = uuid4()
        outbound_message_id = uuid4()
        use_case = _ListDeliveryAttemptsUseCase()

        response = await list_message_delivery_attempts(
            outbound_message_id=outbound_message_id,
            context=SimpleNamespace(principal=SimpleNamespace(tenant_id=tenant_id)),
            use_case=use_case,
            request=ListMessageDeliveryAttemptsRequestSchema(limit=25, offset=50),
        )

        self.assertEqual(use_case.query.tenant_id.uuid, tenant_id)
        self.assertEqual(use_case.query.outbound_message_id.uuid, outbound_message_id)
        self.assertIsNone(use_case.query.status)
        self.assertEqual(use_case.query.limit, 25)
        self.assertEqual(use_case.query.offset, 50)
        self.assertEqual(response.items[0].request_payload, {"body": "hello"})
        self.assertEqual(response.items[0].response_payload, {"status": "sent"})

    async def test_list_delivery_attempts_maps_query_filters(self) -> None:
        tenant_id = uuid4()
        outbound_message_id = uuid4()
        use_case = _ListDeliveryAttemptsUseCase()

        response = await list_delivery_attempts(
            context=SimpleNamespace(principal=SimpleNamespace(tenant_id=tenant_id)),
            use_case=use_case,
            request=ListDeliveryAttemptsRequestSchema(
                outbound_message_id=outbound_message_id,
                status="SUCCESS",
                limit=10,
                offset=20,
            ),
        )

        self.assertEqual(use_case.query.tenant_id.uuid, tenant_id)
        self.assertEqual(use_case.query.outbound_message_id.uuid, outbound_message_id)
        self.assertEqual(use_case.query.status, "SUCCESS")
        self.assertEqual(use_case.query.limit, 10)
        self.assertEqual(use_case.query.offset, 20)
        self.assertEqual(response.items[0].status, "SUCCESS")

    async def test_list_message_delivery_events_maps_path_filter_and_payload(
        self,
    ) -> None:
        tenant_id = uuid4()
        outbound_message_id = uuid4()
        use_case = _ListDeliveryEventsUseCase()

        response = await list_message_delivery_events(
            outbound_message_id=outbound_message_id,
            context=SimpleNamespace(principal=SimpleNamespace(tenant_id=tenant_id)),
            use_case=use_case,
            request=ListMessageDeliveryEventsRequestSchema(limit=25, offset=50),
        )

        self.assertEqual(use_case.query.tenant_id.uuid, tenant_id)
        self.assertEqual(use_case.query.outbound_message_id.uuid, outbound_message_id)
        self.assertIsNone(use_case.query.external_message_id)
        self.assertIsNone(use_case.query.internal_status)
        self.assertIsNone(use_case.query.event_type)
        self.assertEqual(use_case.query.limit, 25)
        self.assertEqual(use_case.query.offset, 50)
        self.assertEqual(response.items[0].raw_payload, {"message_id": "ext-1"})

    async def test_list_delivery_events_maps_query_filters(self) -> None:
        tenant_id = uuid4()
        outbound_message_id = uuid4()
        use_case = _ListDeliveryEventsUseCase()

        response = await list_delivery_events(
            context=SimpleNamespace(principal=SimpleNamespace(tenant_id=tenant_id)),
            use_case=use_case,
            request=ListDeliveryEventsRequestSchema(
                outbound_message_id=outbound_message_id,
                external_message_id="ext-1",
                internal_status="DELIVERED",
                event_type="WEBHOOK_RECEIVED",
                limit=10,
                offset=20,
            ),
        )

        self.assertEqual(use_case.query.tenant_id.uuid, tenant_id)
        self.assertEqual(use_case.query.outbound_message_id.uuid, outbound_message_id)
        self.assertEqual(use_case.query.external_message_id, "ext-1")
        self.assertEqual(use_case.query.internal_status, "DELIVERED")
        self.assertEqual(use_case.query.event_type, "WEBHOOK_RECEIVED")
        self.assertEqual(use_case.query.limit, 10)
        self.assertEqual(use_case.query.offset, 20)
        self.assertEqual(response.items[0].raw_payload, {"message_id": "ext-1"})

    async def test_create_provider_connection_maps_not_found_to_404(self) -> None:
        with self.assertRaises(HTTPException) as caught:
            await create_provider_connection(
                payload=CreateProviderConnectionRequestSchema(
                    provider_connector_id=uuid4(),
                    connection_code="gms",
                    connection_name="GMS",
                    channel_code="SMS",
                ),
                context=_context(),
                use_case=_FailingUseCase(ProviderConnectorNotFoundError()),
            )

        self.assertEqual(caught.exception.status_code, 404)
        self.assertEqual(caught.exception.detail, "Provider connector was not found.")

    async def test_create_template_maps_validation_to_422(self) -> None:
        with self.assertRaises(HTTPException) as caught:
            await create_message_template(
                payload=CreateMessageTemplateRequestSchema(
                    template_code="loan",
                    name="Loan",
                    provider_connector_id=uuid4(),
                    provider_message_type_id=uuid4(),
                    channel_code="SMS",
                    message_class="TRANSACTIONAL",
                ),
                context=_context(),
                use_case=_FailingUseCase(
                    CommunicationValidationError("Template channel mismatch.")
                ),
            )

        self.assertEqual(caught.exception.status_code, 422)
        self.assertEqual(caught.exception.detail, "Template channel mismatch.")

    async def test_list_messages_maps_runtime_conflict_to_409(self) -> None:
        with self.assertRaises(HTTPException) as caught:
            await list_messages(
                context=_context(),
                use_case=_FailingUseCase(RuntimeDataPersistenceError("db failed")),
            )

        self.assertEqual(caught.exception.status_code, 409)
        self.assertEqual(caught.exception.detail, "db failed")

    async def test_list_delivery_events_maps_runtime_conflict_to_409(self) -> None:
        with self.assertRaises(HTTPException) as caught:
            await list_delivery_events(
                context=_context(),
                use_case=_FailingUseCase(RuntimeDataPersistenceError("db failed")),
                request=ListDeliveryEventsRequestSchema(),
            )

        self.assertEqual(caught.exception.status_code, 409)
        self.assertEqual(caught.exception.detail, "db failed")


class CommunicationSendPublishTests(unittest.IsolatedAsyncioTestCase):
    async def test_publish_send_job_after_commit_publishes_queued_message(self) -> None:
        outbound_message_id = uuid4()
        publisher = _PublisherStub()
        repository = _RepositoryStub()
        uow = _UnitOfWorkStub()
        tenant_id = uuid4()

        await publish_send_job_after_commit(
            tenant_id=tenant_id,
            result=SendCommunicationResultDTO(
                communication_request_id=uuid4(),
                outbound_message_id=outbound_message_id,
                status="ACCEPTED",
                internal_status=OutboundMessageStatus.QUEUED.value,
                idempotent=False,
            ),
            repository=repository,
            publisher=publisher,
            uow=uow,
        )

        self.assertEqual(
            publisher.published,
            [(str(tenant_id), str(outbound_message_id), "send_communication")],
        )
        self.assertEqual(len(repository.marked), 1)
        self.assertEqual(repository.marked[0][0], str(tenant_id))
        self.assertEqual(repository.marked[0][1], str(outbound_message_id))
        self.assertEqual(uow.commits, 1)
        self.assertEqual(uow.rollbacks, 0)

    async def test_publish_send_job_after_commit_skips_terminal_message(self) -> None:
        publisher = _PublisherStub()
        repository = _RepositoryStub()
        uow = _UnitOfWorkStub()

        await publish_send_job_after_commit(
            tenant_id=uuid4(),
            result=SendCommunicationResultDTO(
                communication_request_id=uuid4(),
                outbound_message_id=uuid4(),
                status="COMPLETED",
                internal_status=OutboundMessageStatus.SENT.value,
                idempotent=True,
            ),
            repository=repository,
            publisher=publisher,
            uow=uow,
        )

        self.assertEqual(publisher.published, [])
        self.assertEqual(repository.marked, [])
        self.assertEqual(uow.commits, 0)
        self.assertEqual(uow.rollbacks, 0)


__all__ = [
    "CommunicationControllerErrorTests",
    "CommunicationHttpRouterTests",
    "CommunicationSendPublishTests",
]
