"""Business membership rules and orchestration, without a database."""

import unittest
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

from src.modules.crm.domain.contact import Contact, ContactIdVO, ContactNotFoundError
from src.modules.crm.domain.company import CompanyIdVO
from src.modules.crm.domain.links import (
    CompanyContactLinksPolicy,
    CrmLinksChangedError,
    DuplicateCrmLinkError,
    InvalidCrmLinksError,
)
from src.modules.crm.application.links.company_contacts import CompanyContactsService
from src.modules.crm.application.contact.command import UpdateContactCommand
from src.modules.crm.application.contact.use_case import UpdateContactUseCase
from src.modules.shared.domain.domain_error import EntityIdTypeError
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


class ContactLinksDomainTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 9, 27, tzinfo=UTC)
        self.actor = EntityIdVO.from_value(uuid4())
        self.contact = Contact.create(
            contact_id=ContactIdVO.from_value(uuid4()),
            actor_id=self.actor,
            now=self.now,
            first_name="Ada",
        )
        self.a, self.b = (CompanyIdVO.from_value(uuid4()) for _ in range(2))
        self.later = self.now + timedelta(hours=1)

    def test_membership_is_immutable_unique_and_audited(self):
        self.assertTrue(
            self.contact.link_company(self.a, actor_id=self.actor, now=self.later)
        )
        self.assertEqual(self.contact.company_ids, frozenset({self.a}))
        self.assertEqual(self.contact.updated_at, self.later)
        with self.assertRaises(AttributeError):
            self.contact.company_ids.add(self.b)
        with self.assertRaises(AttributeError):
            self.contact.company_ids = frozenset()
        self.assertFalse(
            self.contact.link_company(
                self.a, actor_id=self.actor, now=self.later + timedelta(hours=1)
            )
        )
        self.assertEqual(self.contact.updated_at, self.later)
        self.assertTrue(
            self.contact.unlink_company(self.a, actor_id=self.actor, now=self.later)
        )
        self.assertFalse(
            self.contact.unlink_company(self.a, actor_id=self.actor, now=self.later)
        )

    def test_duplicate_wrong_type_missing_snapshot_and_conflict_do_not_mutate(self):
        self.contact.link_company(self.a, actor_id=self.actor, now=self.now)
        for requested, expected, error in [
            ((self.a, self.a), (self.a,), DuplicateCrmLinkError),
            ((ContactIdVO.from_value(self.a.uuid),), (self.a,), EntityIdTypeError),
            ((self.b,), (), CrmLinksChangedError),
            ((self.b,), None, InvalidCrmLinksError),
        ]:
            with self.subTest(error=error), self.assertRaises(error):
                self.contact.replace_companies(
                    requested=requested,
                    expected=expected,
                    actor_id=self.actor,
                    now=self.later,
                )
            self.assertEqual(self.contact.company_ids, frozenset({self.a}))
            self.assertEqual(self.contact.updated_at, self.now)

    def test_replacement_is_a_set_and_preserves_noop_audit(self):
        self.contact.replace_companies(
            requested=(self.a, self.b), expected=(), actor_id=self.actor, now=self.now
        )
        self.assertFalse(
            self.contact.replace_companies(
                requested=(self.b, self.a),
                expected=(self.a, self.b),
                actor_id=self.actor,
                now=self.later,
            )
        )
        self.assertEqual(self.contact.updated_at, self.now)
        self.assertTrue(
            self.contact.replace_companies(
                requested=(),
                expected=(self.a, self.b),
                actor_id=self.actor,
                now=self.later,
            )
        )

    def test_reverse_policy_checks_snapshot_uniqueness_and_availability(self):
        a, b = (ContactIdVO.from_value(uuid4()) for _ in range(2))
        self.assertEqual(
            CompanyContactLinksPolicy.changes(
                current=(a,), expected=(a,), requested=(b,)
            ),
            (frozenset({b}), frozenset({a})),
        )
        with self.assertRaises(DuplicateCrmLinkError):
            CompanyContactLinksPolicy.changes(current=(), expected=(), requested=(a, a))
        with self.assertRaises(CrmLinksChangedError):
            CompanyContactLinksPolicy.changes(current=(a,), expected=(), requested=(b,))
        with self.assertRaises(CrmLinksChangedError):
            CompanyContactLinksPolicy.ensure_available(
                available=(), expected=(a,), requested=()
            )
        with self.assertRaises(ContactNotFoundError):
            CompanyContactLinksPolicy.ensure_available(
                available=(), expected=(), requested=(a,)
            )


class CompanyLinksApplicationTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tenant = EntityIdVO.from_value(uuid4())
        self.actor = EntityIdVO.from_value(uuid4())
        self.now = datetime(2026, 9, 27, tzinfo=UTC)
        self.clock = SimpleNamespace(now=lambda: self.now)
        self.a, self.b = [
            Contact.create(
                contact_id=ContactIdVO.from_value(uuid4()),
                actor_id=self.actor,
                now=self.now,
                first_name=name,
            )
            for name in ("A", "B")
        ]
        self.company, self.other = (CompanyIdVO.from_value(uuid4()) for _ in range(2))
        self.a.link_company(self.company, actor_id=self.actor, now=self.now)
        self.a.link_company(self.other, actor_id=self.actor, now=self.now)
        self.contacts = SimpleNamespace(
            get_many=AsyncMock(return_value=(self.a, self.b)), save=AsyncMock()
        )
        self.queries = SimpleNamespace(
            linked_contact_ids=AsyncMock(return_value=(self.a.id,))
        )
        self.service = CompanyContactsService(self.contacts, self.queries, self.clock)

    async def test_reverse_edit_calls_roots_and_preserves_other_memberships(self):
        locked = await self.service.lock_contacts(
            self.tenant, requested=(self.b.id,), expected=(self.a.id,)
        )
        self.assertTrue(self.contacts.get_many.await_args.kwargs["for_update"])
        await self.service.apply(
            self.tenant,
            self.company,
            self.actor,
            requested=(self.b.id,),
            expected=(self.a.id,),
            contacts=locked,
        )
        self.assertEqual(self.a.company_ids, frozenset({self.other}))
        self.assertEqual(self.b.company_ids, frozenset({self.company}))
        self.assertEqual(self.contacts.save.await_count, 2)
        for call in self.contacts.save.await_args_list:
            self.assertEqual(call.args[0], self.tenant)

    async def test_conflict_writes_nothing(self):
        with self.assertRaises(CrmLinksChangedError):
            await self.service.apply(
                self.tenant,
                self.company,
                self.actor,
                requested=(self.b.id,),
                expected=(),
                contacts={self.b.id: self.b},
            )
        self.contacts.save.assert_not_awaited()
        self.assertEqual(self.b.company_ids, frozenset())

    async def test_omitted_links_do_not_lock_companies_or_touch_membership(self):
        repository = SimpleNamespace(
            get=AsyncMock(return_value=self.a), save=AsyncMock()
        )
        companies = SimpleNamespace(get=AsyncMock())
        points = SimpleNamespace(sync=AsyncMock())
        read = AsyncMock(return_value="details")
        result = await UpdateContactUseCase(
            repository, self.clock, points, read, companies
        )(UpdateContactCommand(self.tenant, self.actor, self.a.id, "Renamed"))
        self.assertEqual(result, "details")
        companies.get.assert_not_awaited()
        self.assertEqual(self.a.company_ids, frozenset({self.company, self.other}))
        repository.save.assert_awaited_once_with(self.tenant, self.a)
