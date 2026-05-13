from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from uuid import uuid4

from fastapi import HTTPException

from src.modules.communication.application.outbound_message.dto import (
    SendCommunicationResultDTO,
)
from src.modules.communication.application.provider_connection import (
    ProviderConnectionDTO,
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
from src.modules.communication.presentation.http.outbound_message.controller.send_communication import (
    _publish_send_job_after_commit,
)
from src.modules.communication.presentation.http.provider_connection.controller.create_provider_connection import (
    create_provider_connection,
)
from src.modules.communication.presentation.http.provider_connection.requests import (
    CreateProviderConnectionRequestSchema,
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
from src.modules.runtime_data import RuntimeDataPersistenceError
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
        self.assertIn(("POST", "/communication/providers/connections"), routes)
        self.assertIn(("GET", "/communication/providers/connections"), routes)
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
            ("POST", "/communication/webhooks/{tenant_id}/{provider_code}"),
            routes,
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


class CommunicationSendPublishTests(unittest.IsolatedAsyncioTestCase):
    async def test_publish_send_job_after_commit_publishes_queued_message(self) -> None:
        outbound_message_id = uuid4()
        publisher = _PublisherStub()
        repository = _RepositoryStub()
        uow = _UnitOfWorkStub()
        tenant_id = uuid4()

        await _publish_send_job_after_commit(
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

        await _publish_send_job_after_commit(
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
