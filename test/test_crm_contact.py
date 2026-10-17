"""Инварианты Contact и создание через независимые Application-порты."""

from dataclasses import FrozenInstanceError, replace
from datetime import UTC, datetime
import unittest
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

from src.modules.crm.application.contact.command.create_contact.command import (
    CreateContactCommand,
)
from src.modules.crm.application.contact.command.create_contact.handler import (
    CreateContactHandler,
)
from src.modules.crm.domain.contact.aggregate import ContactEntity
from src.modules.crm.domain.contact.error import InvalidContactNameError
from src.modules.crm.domain.contact.value_object.identifier import ContactIdVO
from src.modules.crm.domain.contact.value_object.name import ContactNameVO
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


class ContactDomainTests(unittest.TestCase):
    def test_name_is_normalized_without_changing_internal_characters(self):
        name = ContactNameVO("  Анна-Марія  ", "  O'Neill  Smith\t", " Іванівна ")
        self.assertEqual(
            name, ContactNameVO("Анна-Марія", "O'Neill  Smith", "Іванівна")
        )
        with self.assertRaises(FrozenInstanceError):
            name.first_name = "Other"

    def test_empty_optional_parts_mean_absence(self):
        for value in (None, "", " \t\n"):
            with self.subTest(value=value):
                self.assertIsNone(ContactNameVO("A", value, value).last_name)
                self.assertIsNone(ContactNameVO("A", value, value).middle_name)
        self.assertEqual(ContactNameVO("A"), ContactNameVO("A", None, None))

    def test_required_parts_and_types_are_checked_in_domain(self):
        for field in ("first_name", "last_name", "middle_name"):
            invalid = [0, False, [], {}, b"name", "a" * 256]
            if field == "first_name":
                invalid += [None, "", " \n\t"]
            for value in invalid:
                with self.subTest(field=field, value=value):
                    kwargs = dict(first_name="A", last_name="B", middle_name=None)
                    kwargs[field] = value
                    with self.assertRaises(InvalidContactNameError):
                        ContactNameVO(**kwargs)

    def test_length_limit_applies_after_trimming(self):
        name = ContactNameVO(" " + "a" * 255 + " ", "b" * 255, "c" * 255)
        self.assertEqual(len(name.first_name), 255)
        self.assertEqual(ContactNameVO("A", "B").first_name, "A")

    def test_factory_sets_initial_audit_and_validates_name(self):
        identifier = ContactIdVO(uuid4())
        actor = EntityIdVO(uuid4())
        now = datetime(2026, 9, 28, tzinfo=UTC)
        contact = ContactEntity.create(
            contact_id=identifier,
            actor_id=actor,
            now=now,
            first_name=" A ",
            last_name=" B ",
        )
        self.assertEqual(contact.id, identifier)
        self.assertEqual(contact.name, ContactNameVO("A", "B"))
        self.assertEqual((contact.created_at, contact.updated_at), (now, now))
        self.assertEqual((contact.created_by, contact.updated_by), (actor, actor))
        without_surname = ContactEntity.create(
            contact_id=ContactIdVO(uuid4()),
            actor_id=actor,
            now=now,
            first_name=" Solo ",
        )
        self.assertEqual(without_surname.name, ContactNameVO("Solo"))
        with self.assertRaises(InvalidContactNameError):
            ContactEntity.create(
                contact_id=identifier,
                actor_id=actor,
                now=now,
                first_name=" ",
            )

    def test_update_uses_name_vo_and_preserves_audit_for_unchanged_name(self):
        created_at = datetime(2026, 9, 28, tzinfo=UTC)
        updated_at = datetime(2026, 10, 3, tzinfo=UTC)
        creator, editor = EntityIdVO(uuid4()), EntityIdVO(uuid4())
        contact = ContactEntity.create(
            contact_id=ContactIdVO(uuid4()),
            first_name="A",
            last_name="B",
            actor_id=creator,
            now=created_at,
        )
        self.assertFalse(
            contact.update(
                first_name=" A ",
                last_name=" B ",
                middle_name=None,
                actor_id=editor,
                now=updated_at,
            )
        )
        self.assertEqual(
            (contact.updated_at, contact.updated_by), (created_at, creator)
        )
        self.assertTrue(
            contact.update(
                first_name=" A ",
                last_name=" C ",
                middle_name=" M ",
                actor_id=editor,
                now=updated_at,
            )
        )
        self.assertEqual(contact.name, ContactNameVO("A", "C", "M"))
        self.assertTrue(
            contact.update(
                first_name="A",
                last_name=None,
                middle_name=None,
                actor_id=editor,
                now=updated_at,
            )
        )
        self.assertEqual(contact.name, ContactNameVO("A"))
        self.assertEqual(
            (contact.created_at, contact.created_by), (created_at, creator)
        )
        self.assertEqual((contact.updated_at, contact.updated_by), (updated_at, editor))
        with self.assertRaises(InvalidContactNameError):
            contact.update(
                first_name="",
                last_name="C",
                middle_name=None,
                actor_id=creator,
                now=updated_at,
            )
        self.assertEqual(contact.name, ContactNameVO("A"))


class CreateContactHandlerTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.command = CreateContactCommand(
            actor_id=EntityIdVO(uuid4()),
            first_name=" A ",
            last_name=" B ",
            middle_name=" ",
        )
        self.now = datetime(2026, 9, 28, tzinfo=UTC)
        self.clock = Mock(now=Mock(return_value=self.now))
        self.identifier = uuid4()
        self.uuid_generator = Mock(new=Mock(return_value=self.identifier))
        self.repository = Mock(add=AsyncMock())
        self.handler = CreateContactHandler(
            self.repository, self.clock, self.uuid_generator
        )

    async def test_saves_once_and_returns_created_values(self):
        dto = await self.handler.execute(self.command)
        self.clock.now.assert_called_once_with()
        self.uuid_generator.new.assert_called_once_with()
        self.repository.add.assert_awaited_once()
        (contact,) = self.repository.add.await_args.args
        self.assertEqual(contact.id.uuid, self.identifier)
        self.assertEqual(contact.name, ContactNameVO("A", "B"))
        self.assertEqual(
            (dto.id, dto.created_by, dto.updated_by),
            (
                self.identifier,
                self.command.actor_id.uuid,
                self.command.actor_id.uuid,
            ),
        )
        self.assertEqual((dto.created_at, dto.updated_at), (self.now, self.now))
        self.assertEqual(
            (dto.first_name, dto.last_name, dto.middle_name), ("A", "B", None)
        )
        self.assertEqual(contact.created_by, self.command.actor_id)

    async def test_invalid_name_never_reaches_repository(self):
        with self.assertRaises(InvalidContactNameError):
            await self.handler.execute(replace(self.command, first_name=""))
        self.repository.add.assert_not_awaited()

    async def test_storage_failure_propagates(self):
        error = RuntimeError("storage unavailable")
        self.repository.add.side_effect = error
        with self.assertRaises(RuntimeError) as result:
            await self.handler.execute(self.command)
        self.assertIs(result.exception, error)
