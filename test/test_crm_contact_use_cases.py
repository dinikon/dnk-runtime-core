from __future__ import annotations

import unittest
from datetime import UTC, datetime
from uuid import uuid4

from src.modules.crm.application.contact.command.create_contact_command import (
    CreateContactCommand,
)
from src.modules.crm.application.contact.command.rename_contact_command import (
    RenameContactCommand,
)
from src.modules.crm.application.contact.use_case.create_contact import (
    CreateContactUseCase,
)
from src.modules.crm.application.contact.use_case.update_contact import (
    UpdateContactUseCase,
)
from src.modules.crm.domain.contact.entity import ContactEntity
from src.modules.crm.domain.contact.value_object import ContactIdVO
from src.modules.shared import EntityIdVO


class ContactUseCaseTests(unittest.IsolatedAsyncioTestCase):
    async def test_create_contact_passes_status_and_tags_to_service(self) -> None:
        tenant_id = EntityIdVO.from_value(uuid4())
        contact_id = ContactIdVO.from_value(uuid4())
        now = datetime.now(UTC)
        recorded: dict[str, object] = {}

        class ServiceStub:
            async def create_contact(self, **kwargs):
                recorded.update(kwargs)
                return ContactEntity.create(
                    id_=contact_id,
                    now=now,
                    first_name="Jane",
                    last_name="Doe",
                    middle_name=None,
                    status="customer",
                    tags=("vip", "newsletter"),
                )

        use_case = CreateContactUseCase(ServiceStub())

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

        self.assertEqual(recorded["status"], "customer")
        self.assertEqual(recorded["tags"], ("vip", "newsletter"))
        self.assertEqual(result.status, "customer")
        self.assertEqual(result.tags, ["vip", "newsletter"])

    async def test_update_contact_passes_status_and_tags_to_service(self) -> None:
        tenant_id = EntityIdVO.from_value(uuid4())
        contact_id = ContactIdVO.from_value(uuid4())
        now = datetime.now(UTC)
        recorded: dict[str, object] = {}

        class ServiceStub:
            async def rename_contact(self, **kwargs):
                recorded.update(kwargs)
                return ContactEntity.create(
                    id_=contact_id,
                    now=now,
                    first_name="Jane",
                    last_name="Doe",
                    middle_name=None,
                    status="partner",
                    tags=(),
                )

        use_case = UpdateContactUseCase(ServiceStub())

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

        self.assertEqual(recorded["status"], "partner")
        self.assertEqual(recorded["tags"], ())
        self.assertEqual(result.status, "partner")
        self.assertEqual(result.tags, [])
