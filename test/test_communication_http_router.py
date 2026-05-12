from __future__ import annotations

from datetime import datetime
import unittest
from uuid import uuid4

from src.modules.communication.application.dto import SendCommunicationResultDTO
from src.modules.communication.domain import OutboundMessageStatus
from src.modules.communication.presentation.http.router import (
    _publish_send_job_after_commit,
)
from src.modules.communication.presentation.http.router import router


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
    "CommunicationHttpRouterTests",
    "CommunicationSendPublishTests",
]
