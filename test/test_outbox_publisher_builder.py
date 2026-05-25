from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import patch

from src.config.infrastructure.event_bus_config import EventBusSettings
from src.modules.shared.application.events import PublishOutboxResultDTO
import src.modules.shared.presentation.events.outbox_publisher_builder as builder


class _UnitOfWorkStub:
    def __init__(self) -> None:
        self.session = object()
        self.commits = 0

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None

    async def commit(self) -> None:
        self.commits += 1


class OutboxPublisherBuilderTests(unittest.IsolatedAsyncioTestCase):
    async def test_publish_once_uses_new_uow_and_commits_batch(self) -> None:
        created_uows = []
        recorded = {}

        def uow_factory():
            uow = _UnitOfWorkStub()
            created_uows.append(uow)
            return uow

        class RepositoryStub:
            def __init__(self, session) -> None:
                recorded["session"] = session

        class BrokerPublisherStub:
            def __init__(self, broker_provider) -> None:
                recorded["broker_provider"] = broker_provider

        class EventPublisherStub:
            def __init__(self, *, broker_publisher, settings) -> None:
                recorded["broker_publisher"] = broker_publisher
                recorded["settings"] = settings

        class UseCaseStub:
            def __init__(
                self,
                *,
                repository,
                publisher,
                clock,
                retry_base_seconds,
            ) -> None:
                recorded["repository"] = repository
                recorded["publisher"] = publisher
                recorded["clock"] = clock
                recorded["retry_base_seconds"] = retry_base_seconds

            async def __call__(self, command):
                recorded["command"] = command
                return PublishOutboxResultDTO(scanned=2, published=2, failed=0)

        settings = EventBusSettings(
            publish_limit=12,
            max_attempts=4,
            retry_base_seconds=9,
        )
        config = SimpleNamespace(EVENT_BUS=settings)
        clock = object()
        broker_provider = object()

        with (
            patch.object(builder, "SqlAlchemyOutboxRepository", RepositoryStub),
            patch.object(builder, "RabbitMQBrokerPublisher", BrokerPublisherStub),
            patch.object(
                builder,
                "RabbitMQIntegrationEventPublisher",
                EventPublisherStub,
            ),
            patch.object(builder, "PublishOutboxEventsUseCase", UseCaseStub),
        ):
            publish_once = builder.build_publish_once(
                config=config,
                uow_factory=uow_factory,
                clock=clock,
                broker_provider=broker_provider,
            )
            result = await publish_once()

        self.assertEqual(result.published, 2)
        self.assertEqual(len(created_uows), 1)
        self.assertEqual(created_uows[0].commits, 1)
        self.assertIs(recorded["session"], created_uows[0].session)
        self.assertIs(recorded["broker_provider"], broker_provider)
        self.assertIs(recorded["settings"], settings)
        self.assertIs(recorded["clock"], clock)
        self.assertEqual(recorded["retry_base_seconds"], 9)
        self.assertEqual(recorded["command"].limit, 12)
        self.assertEqual(recorded["command"].max_attempts, 4)


__all__ = ["OutboxPublisherBuilderTests"]
