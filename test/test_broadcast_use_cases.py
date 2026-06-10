from __future__ import annotations

import unittest
from datetime import UTC, datetime
from uuid import uuid4

from src.modules.broadcast.application.broadcast.command import CreateBroadcastCommand
from src.modules.broadcast.application.broadcast.use_case import CreateBroadcastUseCase
from src.modules.broadcast.domain.broadcast.value_object.broadcast_id import (
    BroadcastIdVO,
)
from src.modules.shared import EntityIdVO


class BroadcastUseCaseTests(unittest.IsolatedAsyncioTestCase):
    async def test_create_broadcast_saves_draft_entity(self) -> None:
        tenant_id = uuid4()
        broadcast_id = uuid4()
        now = datetime.now(UTC)

        class ClockStub:
            def now(self):
                return now

        class UuidGeneratorStub:
            def new(self):
                return broadcast_id

        class RepositoryStub:
            saved_tenant_id = None
            saved_broadcast = None

            async def load(self, *, tenant_id, broadcast_id):
                raise AssertionError("load should not be called")

            async def save(self, *, tenant_id, broadcast):
                self.saved_tenant_id = tenant_id
                self.saved_broadcast = broadcast
                return broadcast

        repository = RepositoryStub()
        use_case = CreateBroadcastUseCase(
            command_repository=repository,
            clock=ClockStub(),
            uuid_generator=UuidGeneratorStub(),
        )

        result = await use_case(
            CreateBroadcastCommand(
                tenant_id=tenant_id,
                title="  June broadcast  ",
                description=None,
            )
        )

        self.assertEqual(repository.saved_tenant_id, EntityIdVO.from_value(tenant_id))
        self.assertIsNotNone(repository.saved_broadcast)
        assert repository.saved_broadcast is not None
        self.assertEqual(
            repository.saved_broadcast.id,
            BroadcastIdVO.from_value(broadcast_id),
        )
        self.assertEqual(repository.saved_broadcast.created_at, now)
        self.assertEqual(repository.saved_broadcast.updated_at, now)
        self.assertEqual(repository.saved_broadcast.title.value, "June broadcast")
        self.assertIsNone(repository.saved_broadcast.description)
        self.assertEqual(repository.saved_broadcast.status.value, "DRAFT")
        self.assertEqual(result.id, broadcast_id)
        self.assertEqual(result.title, "June broadcast")
        self.assertIsNone(result.description)
        self.assertEqual(result.status, "DRAFT")
