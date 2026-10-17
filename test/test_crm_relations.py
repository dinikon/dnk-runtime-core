"""Связь Contact–Company без отдельного агрегата и SQL-схемы на запросе."""

from dataclasses import FrozenInstanceError
from datetime import UTC, datetime
from typing import cast
import unittest
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

from sqlalchemy.dialects import postgresql
from sqlalchemy.engine import RowMapping

from src.modules.crm.application.company.query.list_contacts.handler import (
    ListCompanyContactsHandler,
)
from src.modules.crm.application.company.query.list_contacts.query import (
    ListCompanyContactsQuery,
)
from src.modules.crm.application.contact.command.link_company.command import (
    LinkCompanyCommand,
)
from src.modules.crm.application.contact.command.link_company.handler import (
    LinkCompanyHandler,
)
from src.modules.crm.application.contact.command.unlink_company.command import (
    UnlinkCompanyCommand,
)
from src.modules.crm.application.contact.command.unlink_company.handler import (
    UnlinkCompanyHandler,
)
from src.modules.crm.application.contact.query.list_companies.handler import (
    ListContactCompaniesHandler,
)
from src.modules.crm.application.contact.query.list_companies.query import (
    ListContactCompaniesQuery,
)
from src.modules.crm.domain.company.error import CompanyNotFoundError
from src.modules.crm.domain.company.value_object.identifier import CompanyIdVO
from src.modules.crm.domain.contact.error import (
    ContactNotFoundError,
    InvalidContactCompanyLinkError,
)
from src.modules.crm.domain.contact.value_object.company_link import (
    ContactCompanyLinkVO,
)
from src.modules.crm.domain.contact.value_object.identifier import ContactIdVO
from src.modules.crm.infrastructure.company.persistence.contact_link_query_repository import (
    SqlAlchemyCompanyContactQueryRepository,
)
from src.modules.crm.infrastructure.contact.persistence.company_link_query_repository import (
    SqlAlchemyContactCompanyQueryRepository,
)
from src.modules.crm.infrastructure.contact.persistence.company_link_repository import (
    SqlAlchemyCompanyLinkRepository,
)


class ContactCompanyDomainTests(unittest.TestCase):
    def test_link_pair_is_typed_and_immutable(self):
        link = ContactCompanyLinkVO(ContactIdVO(uuid4()), CompanyIdVO(uuid4()))
        with self.assertRaises(FrozenInstanceError):
            link.contact_id = ContactIdVO(uuid4())
        for first, second in (
            (CompanyIdVO(uuid4()), CompanyIdVO(uuid4())),
            (ContactIdVO(uuid4()), ContactIdVO(uuid4())),
        ):
            with self.subTest(first=first, second=second):
                with self.assertRaises(InvalidContactCompanyLinkError):
                    ContactCompanyLinkVO(first, second)


class ContactCompanyHandlerTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.contact_id, self.company_id = ContactIdVO(uuid4()), CompanyIdVO(uuid4())
        self.repository = Mock(
            lock_contact=AsyncMock(return_value=True),
            lock_company=AsyncMock(return_value=True),
            link=AsyncMock(),
            unlink=AsyncMock(),
        )

    async def test_link_and_unlink_use_contact_first_for_both_directions(self):
        order = []

        async def contact(_):
            order.append("contact")
            return True

        async def company(_):
            order.append("company")
            return True

        self.repository.lock_contact.side_effect = contact
        self.repository.lock_company.side_effect = company
        await LinkCompanyHandler(self.repository).execute(
            LinkCompanyCommand(self.contact_id, self.company_id)
        )
        await UnlinkCompanyHandler(self.repository).execute(
            UnlinkCompanyCommand(self.contact_id, self.company_id)
        )
        self.assertEqual(order, ["contact", "company", "contact", "company"])
        pair = ContactCompanyLinkVO(self.contact_id, self.company_id)
        self.repository.link.assert_awaited_once_with(pair)
        self.repository.unlink.assert_awaited_once_with(pair)

    async def test_absent_contact_stops_before_company_or_write(self):
        self.repository.lock_contact.return_value = False
        with self.assertRaises(ContactNotFoundError):
            await LinkCompanyHandler(self.repository).execute(
                LinkCompanyCommand(self.contact_id, self.company_id)
            )
        self.repository.lock_company.assert_not_awaited()
        self.repository.link.assert_not_awaited()

    async def test_absent_company_stops_before_write(self):
        self.repository.lock_company.return_value = False
        with self.assertRaises(CompanyNotFoundError):
            await UnlinkCompanyHandler(self.repository).execute(
                UnlinkCompanyCommand(self.contact_id, self.company_id)
            )
        self.repository.unlink.assert_not_awaited()

    async def test_list_handlers_distinguish_missing_owner_and_empty_links(self):
        contact_repo = Mock(list_companies=AsyncMock(return_value=[]))
        company_repo = Mock(list_contacts=AsyncMock(return_value=[]))
        contact_handler = ListContactCompaniesHandler(contact_repo)
        company_handler = ListCompanyContactsHandler(company_repo)
        self.assertEqual(
            (
                await contact_handler.execute(
                    ListContactCompaniesQuery(self.contact_id)
                )
            ).companies,
            (),
        )
        self.assertEqual(
            (
                await company_handler.execute(ListCompanyContactsQuery(self.company_id))
            ).contacts,
            (),
        )
        contact_repo.list_companies.return_value = None
        company_repo.list_contacts.return_value = None
        with self.assertRaises(ContactNotFoundError):
            await contact_handler.execute(ListContactCompaniesQuery(self.contact_id))
        with self.assertRaises(CompanyNotFoundError):
            await company_handler.execute(ListCompanyContactsQuery(self.company_id))


class ContactCompanyPersistenceTests(unittest.IsolatedAsyncioTestCase):
    async def test_writes_use_locks_and_idempotent_insert(self):
        result = Mock(scalar_one_or_none=Mock(return_value=uuid4()))
        session = Mock(execute=AsyncMock(return_value=result))
        repository = SqlAlchemyCompanyLinkRepository(session)
        contact_id, company_id = ContactIdVO(uuid4()), CompanyIdVO(uuid4())
        self.assertTrue(await repository.lock_contact(contact_id))
        self.assertTrue(await repository.lock_company(company_id))
        for call in session.execute.await_args_list:
            statement = call.args[0]
            self.assertIn(
                "FOR KEY SHARE", str(statement.compile(dialect=postgresql.dialect()))
            )
            self.assertNotIn("schema_translate_map", statement.get_execution_options())
        link = ContactCompanyLinkVO(contact_id, company_id)
        await repository.link(link)
        insert = session.execute.await_args.args[0]
        self.assertIn(
            "ON CONFLICT (contact_id, company_id) DO NOTHING",
            str(insert.compile(dialect=postgresql.dialect())),
        )
        await repository.unlink(link)
        delete = session.execute.await_args.args[0]
        self.assertTrue(str(delete.compile()).startswith("DELETE FROM "))
        self.assertNotIn("schema_translate_map", delete.get_execution_options())

    async def test_each_list_is_one_outer_join_and_distinguishes_absence(self):
        now, actor = datetime(2026, 10, 4, tzinfo=UTC), uuid4()
        contact_id, company_id = ContactIdVO(uuid4()), CompanyIdVO(uuid4())
        company_row = dict(
            owner_id=contact_id.uuid,
            id=company_id.uuid,
            legal_name="ACME",
            created_at=now,
            updated_at=now,
            created_by=actor,
            updated_by=actor,
        )
        contact_row = dict(
            owner_id=company_id.uuid,
            id=contact_id.uuid,
            first_name="A",
            last_name=None,
            middle_name=None,
            created_at=now,
            updated_at=now,
            created_by=actor,
            updated_by=actor,
        )
        for repository_type, method_name, identifier, row, expected in (
            (
                SqlAlchemyContactCompanyQueryRepository,
                "list_companies",
                contact_id,
                company_row,
                "legal_name",
            ),
            (
                SqlAlchemyCompanyContactQueryRepository,
                "list_contacts",
                company_id,
                contact_row,
                "first_name",
            ),
        ):
            with self.subTest(repository=repository_type):
                result = Mock()
                result.mappings.return_value.all.return_value = [cast(RowMapping, row)]
                session = Mock(execute=AsyncMock(return_value=result))
                repository = repository_type(session)
                items = await getattr(repository, method_name)(identifier)
                self.assertEqual(getattr(items[0], expected), row[expected])
                statement = session.execute.await_args.args[0]
                sql = str(statement.compile())
                self.assertIn("LEFT OUTER JOIN", sql)
                self.assertIn("ORDER BY", sql)
                self.assertNotIn(
                    "schema_translate_map", statement.get_execution_options()
                )
                session.execute.assert_awaited_once()
                result.mappings.return_value.all.return_value = [
                    cast(RowMapping, {**row, "id": None})
                ]
                self.assertEqual(await getattr(repository, method_name)(identifier), [])
                result.mappings.return_value.all.return_value = []
                self.assertIsNone(await getattr(repository, method_name)(identifier))
