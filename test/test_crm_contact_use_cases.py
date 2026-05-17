from __future__ import annotations

import unittest
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from src.modules.crm.application.contact.command.create_contact_command import (
    CreateContactCommand,
)
from src.modules.crm.application.contact.command.delete_contact_command import (
    DeleteContactCommand,
)
from src.modules.crm.application.contact.command.rename_contact_command import (
    RenameContactCommand,
)
from src.modules.crm.application.contact.use_case.create_contact import (
    CreateContactUseCase,
)
from src.modules.crm.application.contact.use_case.delete_contact import (
    DeleteContactUseCase,
)
from src.modules.crm.application.contact.query.list_contacts_query import (
    ListContactsQuery,
)
from src.modules.crm.application.contact.use_case.list_contacts import (
    ListContactsUseCase,
)
from src.modules.crm.application.contact.use_case.update_contact import (
    UpdateContactUseCase,
)
from src.modules.crm.domain.contact.entity import ContactEntity
from src.modules.crm.domain.contact.error import ContactNotFoundError
from src.modules.crm.domain.contact.value_object import ContactIdVO
from src.modules.runtime_data.application.query.result import (
    RuntimeRecordDTO,
    RuntimeSearchRecordsResult,
)
from src.modules.shared import EntityIdVO


class ContactUseCaseTests(unittest.IsolatedAsyncioTestCase):

    async def test_create_contact_saves_entity_with_status_and_tags(self) -> None:
        tenant_id = EntityIdVO.from_value(uuid4())
        contact_id = ContactIdVO.from_value(uuid4())
        now = datetime.now(UTC)

        class ClockStub:
            def now(self):
                return now

        class RepositoryStub:
            saved_tenant_id = None
            saved_contact = None

            async def load(self, *, tenant_id, contact_id):
                raise AssertionError("load should not be called")

            async def save(self, *, tenant_id, contact):
                self.saved_tenant_id = tenant_id
                self.saved_contact = contact
                return contact

            async def delete(self, *, tenant_id, contact_id):
                raise AssertionError("delete should not be called")

        repository = RepositoryStub()
        use_case = CreateContactUseCase(
            command_repository=repository,
            clock=ClockStub(),
        )

        result = await use_case(
            CreateContactCommand(
                tenant_id=tenant_id,
                contact_id=contact_id,
                first_name="Jane",
                last_name="Doe",
                status="customer",
                tags=("vip", "newsletter"),
            )
        )

        self.assertEqual(repository.saved_tenant_id, tenant_id)
        self.assertIsNotNone(repository.saved_contact)
        assert repository.saved_contact is not None
        self.assertEqual(repository.saved_contact.id, contact_id)
        self.assertEqual(repository.saved_contact.created_at, now)
        self.assertEqual(repository.saved_contact.updated_at, now)
        self.assertEqual(repository.saved_contact.status, "customer")
        self.assertEqual(repository.saved_contact.tags, ["vip", "newsletter"])
        self.assertEqual(result.status, "customer")
        self.assertEqual(result.tags, ["vip", "newsletter"])

    async def test_update_contact_loads_renames_and_saves_entity(self) -> None:
        tenant_id = EntityIdVO.from_value(uuid4())
        contact_id = ContactIdVO.from_value(uuid4())
        now = datetime.now(UTC)
        updated_at = now + timedelta(minutes=1)
        contact = ContactEntity.create(
            id_=contact_id,
            now=now,
            first_name="Janet",
            last_name="Doe",
            status="lead",
            tags=("vip",),
        )

        class ClockStub:
            def now(self):
                return updated_at

        class RepositoryStub:
            loaded = False
            saved_contact = None

            async def load(self, *, tenant_id, contact_id):
                self.loaded = True
                return contact

            async def save(self, *, tenant_id, contact):
                self.saved_contact = contact
                return contact

            async def delete(self, *, tenant_id, contact_id):
                raise AssertionError("delete should not be called")

        repository = RepositoryStub()
        use_case = UpdateContactUseCase(
            command_repository=repository,
            clock=ClockStub(),
        )

        result = await use_case(
            RenameContactCommand(
                tenant_id=tenant_id,
                contact_id=contact_id,
                first_name="Jane",
                last_name="Doe",
                status="partner",
                tags=(),
            )
        )

        self.assertTrue(repository.loaded)
        self.assertIs(repository.saved_contact, contact)
        self.assertEqual(contact.updated_at, updated_at)
        self.assertEqual(contact.status, "partner")
        self.assertEqual(contact.tags, [])
        self.assertEqual(result.status, "partner")
        self.assertEqual(result.tags, [])

    async def test_delete_contact_loads_before_delete(self) -> None:
        tenant_id = EntityIdVO.from_value(uuid4())
        contact_id = ContactIdVO.from_value(uuid4())
        contact = ContactEntity.create(
            id_=contact_id,
            now=datetime.now(UTC),
            first_name="Jane",
        )

        class RepositoryStub:
            deleted = False

            async def load(self, *, tenant_id, contact_id):
                return contact

            async def save(self, *, tenant_id, contact):
                raise AssertionError("save should not be called")

            async def delete(self, *, tenant_id, contact_id):
                self.deleted = True

        repository = RepositoryStub()
        use_case = DeleteContactUseCase(repository)

        await use_case(
            DeleteContactCommand(
                tenant_id=tenant_id,
                contact_id=contact_id,
            )
        )

        self.assertTrue(repository.deleted)

    async def test_list_contacts_delegates_raw_dsl_to_runtime_query_service(
        self,
    ) -> None:
        tenant_id = EntityIdVO.from_value(uuid4())
        contact_id = uuid4()
        now = datetime.now(UTC)
        recorded_query = None

        class RuntimeQueryServiceSpy:
            async def search_records(self, query):
                nonlocal recorded_query
                recorded_query = query
                return RuntimeSearchRecordsResult(
                    rows=(
                        RuntimeRecordDTO(
                            id=contact_id,
                            values={
                                "id": contact_id,
                                "created_at": now,
                                "updated_at": now,
                                "last_name": "Doe",
                                "first_name": "Jane",
                                "middle_name": None,
                                "status": "lead",
                                "tags": ["vip"],
                            },
                        ),
                    ),
                    total=7,
                    limit=query.limit,
                    offset=query.offset,
                )

        use_case = ListContactsUseCase(RuntimeQueryServiceSpy())
        filter_dsl = {"field": "status", "op": "eq", "value": "lead"}
        sort_dsl = [{"field": "created_at", "direction": "desc"}]

        result = await use_case(
            ListContactsQuery(
                tenant_id=tenant_id,
                filter_dsl=filter_dsl,
                sort_dsl=sort_dsl,
                limit=10,
                offset=5,
            )
        )

        self.assertEqual(recorded_query.tenant_id, tenant_id)
        self.assertEqual(recorded_query.object_name, "contact")
        self.assertEqual(recorded_query.filter_dsl, filter_dsl)
        self.assertEqual(recorded_query.sort_dsl, sort_dsl)
        self.assertEqual(result.total, 7)
        self.assertEqual(result.items[0].id, contact_id)
        self.assertEqual(result.items[0].tags, ["vip"])

    async def test_delete_contact_raises_when_contact_is_missing(self) -> None:
        tenant_id = EntityIdVO.from_value(uuid4())
        contact_id = ContactIdVO.from_value(uuid4())

        class RepositoryStub:
            async def load(self, *, tenant_id, contact_id):
                return None

            async def save(self, *, tenant_id, contact):
                raise AssertionError("save should not be called")

            async def delete(self, *, tenant_id, contact_id):
                raise AssertionError("delete should not be called")

        use_case = DeleteContactUseCase(RepositoryStub())

        with self.assertRaises(ContactNotFoundError):
            await use_case(
                DeleteContactCommand(
                    tenant_id=tenant_id,
                    contact_id=contact_id,
                )
            )
