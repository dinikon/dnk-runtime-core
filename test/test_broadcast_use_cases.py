from __future__ import annotations

import unittest
from datetime import UTC, datetime
from uuid import uuid4

from src.modules.broadcast.application.broadcast.command import CreateBroadcastCommand
from src.modules.broadcast.application.broadcast.dto import (
    BroadcastDTO,
    BroadcastFieldsDescriptionDTO,
    BroadcastListDTO,
    BroadcastObjectDescriptionDTO,
)
from src.modules.broadcast.application.broadcast.query import ListBroadcastsQuery
from src.modules.broadcast.application.broadcast.use_case import (
    CreateBroadcastUseCase,
    DescribeBroadcastFieldsUseCase,
    ListBroadcastsUseCase,
)
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

    async def test_list_broadcasts_delegates_to_query_repository(self) -> None:
        tenant_id = uuid4()
        broadcast_id = uuid4()
        now = datetime.now(UTC)
        filter_dsl = {"field": "status", "op": "eq", "value": "DRAFT"}
        sort_dsl = [{"field": "created_at", "direction": "desc"}]
        expected = BroadcastListDTO(
            items=(
                BroadcastDTO(
                    id=broadcast_id,
                    created_at=now,
                    updated_at=now,
                    title="June broadcast",
                    description=None,
                    status="DRAFT",
                ),
            ),
            total=1,
            limit=25,
            offset=50,
        )

        class RepositoryStub:
            list_kwargs = None

            async def list(self, **kwargs):
                self.list_kwargs = kwargs
                return expected

        repository = RepositoryStub()
        use_case = ListBroadcastsUseCase(query_repository=repository)

        result = await use_case(
            ListBroadcastsQuery(
                tenant_id=tenant_id,
                filter_dsl=filter_dsl,
                sort_dsl=sort_dsl,
                limit=25,
                offset=50,
            )
        )

        self.assertEqual(result, expected)
        self.assertIsNotNone(repository.list_kwargs)
        assert repository.list_kwargs is not None
        self.assertEqual(
            repository.list_kwargs["tenant_id"],
            EntityIdVO.from_value(tenant_id),
        )
        self.assertEqual(repository.list_kwargs["filter_dsl"], filter_dsl)
        self.assertEqual(repository.list_kwargs["sort_dsl"], sort_dsl)
        self.assertEqual(repository.list_kwargs["limit"], 25)
        self.assertEqual(repository.list_kwargs["offset"], 50)

    async def test_describe_broadcast_fields_delegates_to_repository(self) -> None:
        tenant_id = EntityIdVO.from_value(uuid4())
        expected = BroadcastFieldsDescriptionDTO(
            object_description=BroadcastObjectDescriptionDTO(
                id=uuid4(),
                singular_label="Broadcast",
                plural_label="Broadcasts",
                description="Tenant broadcast definitions.",
                kind="standard",
            ),
            fields=(),
        )

        class RepositoryStub:
            described_tenant_id = None

            async def describe_fields(self, *, tenant_id):
                self.described_tenant_id = tenant_id
                return expected

        repository = RepositoryStub()
        use_case = DescribeBroadcastFieldsUseCase(repository)

        result = await use_case(tenant_id)

        self.assertEqual(result, expected)
        self.assertEqual(repository.described_tenant_id, tenant_id)
