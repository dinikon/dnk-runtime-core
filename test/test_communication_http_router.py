from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace
import unittest
from uuid import uuid4

from fastapi import HTTPException

from src.modules.communication.application.dto import SendCommunicationResultDTO
from src.modules.communication.domain.error import (
    CommunicationValidationError,
)
from src.modules.communication.domain.outbound_message import (
    OutboundMessageStatus,
)
from src.modules.communication.domain.provider_connector import (
    ProviderConnectorNotFoundError,
)
from src.modules.communication.presentation.http.message.router import list_messages
from src.modules.communication.presentation.http.provider.router import (
    CreateProviderConnectionRequestSchema,
    create_provider_connection,
)
from src.modules.communication.presentation.http.template.router import (
    CreateMessageTemplateRequestSchema,
    create_message_template,
)
from src.modules.communication.presentation.http.router import (
    _publish_send_job_after_commit,
)
from src.modules.communication.presentation.http.router import router
from src.modules.runtime_data import RuntimeDataPersistenceError


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


def _context():
    return SimpleNamespace(principal=SimpleNamespace(tenant_id=uuid4()))


class CommunicationControllerErrorTests(unittest.IsolatedAsyncioTestCase):
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
