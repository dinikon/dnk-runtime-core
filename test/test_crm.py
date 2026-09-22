import unittest
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

from sqlalchemy import CheckConstraint, Index

from src.modules.crm.application.company.command import (
    CreateCompanyCommand,
    DeleteCompanyCommand,
    UpdateCompanyCommand,
)
from src.modules.crm.application.company.query import (
    GetCompanyQuery,
    ListCompaniesQuery,
)
from src.modules.crm.application.company.use_case import (
    CreateCompanyUseCase,
    DeleteCompanyUseCase,
    GetCompanyUseCase,
    ListCompaniesUseCase,
    UpdateCompanyUseCase,
)
from src.modules.crm.application.contact.command import (
    CreateContactCommand,
    DeleteContactCommand,
    UpdateContactCommand,
)
from src.modules.crm.application.contact.query import (
    GetContactQuery,
    ListContactsQuery,
)
from src.modules.crm.application.contact.use_case import (
    CreateContactUseCase,
    DeleteContactUseCase,
    GetContactUseCase,
    ListContactsUseCase,
    UpdateContactUseCase,
)
from src.modules.crm.domain.company import (
    Company,
    CompanyIdVO,
    CompanyNotFoundError,
    InvalidCompanyNameError,
)
from src.modules.crm.domain.contact import (
    Contact,
    ContactIdVO,
    ContactNotFoundError,
    InvalidContactNameError,
)
from src.modules.crm.infrastructure.persistence import CompanyModel, ContactModel
from src.modules.crm.infrastructure.persistence.company_repository import (
    SqlAlchemyCompanyRepository,
    company_entity,
)
from src.modules.crm.infrastructure.persistence.contact_repository import (
    SqlAlchemyContactRepository,
    contact_entity,
)
from src.modules.shared.application.persistence.tenant_schema_naming import (
    TenantSchemaNaming,
)
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.shared.infrastructure.persistence import Base, TenantBase
from src.modules.shared.infrastructure.persistence.tenant_migration_metadata import (
    managed_table_names,
    migration_metadata,
)


class FixedClock:
    def __init__(self, value: datetime):
        self.value = value

    def now(self) -> datetime:
        return self.value


class CrmDomainTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 9, 22, 10, 0, tzinfo=UTC)
        self.actor = EntityIdVO.from_value(uuid4())

    def contact(self, **changes):
        values = dict(
            contact_id=ContactIdVO.from_value(uuid4()),
            actor_id=self.actor,
            now=self.now,
            first_name=" Іван ",
            last_name=" Петренко ",
            middle_name=" ",
        )
        values.update(changes)
        return Contact.create(**values)

    def company(self, **changes):
        values = dict(
            company_id=CompanyIdVO.from_value(uuid4()),
            actor_id=self.actor,
            now=self.now,
            name=" Acme Ukraine ",
        )
        values.update(changes)
        return Company.create(**values)

    def test_contact_normalizes_name_and_initializes_audit(self):
        contact = self.contact()
        self.assertEqual(contact.name.first_name, "Іван")
        self.assertEqual(contact.name.last_name, "Петренко")
        self.assertIsNone(contact.name.middle_name)
        self.assertEqual(contact.name.display_name, "Петренко Іван")
        self.assertEqual(contact.created_at, contact.updated_at)
        self.assertEqual(contact.created_by, contact.updated_by)

    def test_contact_rejects_invalid_names(self):
        for changes in (
            {"first_name": ""},
            {"first_name": " "},
            {"first_name": "x" * 256},
            {"first_name": None},
            {"last_name": "x" * 256},
            {"middle_name": 42},
        ):
            with (
                self.subTest(changes=changes),
                self.assertRaises(InvalidContactNameError),
            ):
                self.contact(**changes)

        padded = self.contact(first_name=f"  {'x' * 255}  ")
        self.assertEqual(padded.name.first_name, "x" * 255)

    def test_contact_noop_preserves_update_audit(self):
        contact = self.contact()
        next_actor = EntityIdVO.from_value(uuid4())
        changed = contact.update(
            actor_id=next_actor,
            now=self.now + timedelta(hours=1),
            first_name="Іван",
            last_name="Петренко",
            middle_name=None,
        )
        self.assertFalse(changed)
        self.assertEqual(contact.updated_at, self.now)
        self.assertEqual(contact.updated_by, self.actor)
        self.assertTrue(
            contact.update(
                actor_id=next_actor,
                now=self.now + timedelta(hours=1),
                first_name="Іванко",
                last_name="Петренко",
                middle_name=None,
            )
        )
        self.assertEqual(contact.updated_by, next_actor)

    def test_company_normalizes_validates_and_preserves_noop_audit(self):
        company = self.company()
        self.assertEqual(company.name.value, "Acme Ukraine")
        self.assertFalse(
            company.update(
                actor_id=EntityIdVO.from_value(uuid4()),
                now=self.now + timedelta(hours=1),
                name=" Acme Ukraine ",
            )
        )
        self.assertEqual(company.updated_at, self.now)
        for name in ("", " ", "x" * 256, None):
            with self.subTest(name=name), self.assertRaises(InvalidCompanyNameError):
                self.company(name=name)


class CrmUseCaseTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.now = datetime(2026, 9, 22, 10, 0, tzinfo=UTC)
        self.clock = FixedClock(self.now)
        self.tenant_id = EntityIdVO.from_value(uuid4())
        self.actor_id = EntityIdVO.from_value(uuid4())

    async def test_contact_create_update_noop_and_delete(self):
        repository = SimpleNamespace(
            add=AsyncMock(), save=AsyncMock(), get=AsyncMock(), delete=AsyncMock()
        )
        contact_id = ContactIdVO.from_value(uuid4())
        created = await CreateContactUseCase(repository, self.clock)(
            CreateContactCommand(
                self.tenant_id,
                self.actor_id,
                contact_id,
                " Іван ",
                " Петренко ",
                None,
            )
        )
        self.assertEqual(created.first_name, "Іван")
        repository.add.assert_awaited_once()
        self.assertEqual(repository.add.await_args.args[0], self.tenant_id)
        entity = repository.add.await_args.args[1]
        repository.get.return_value = entity
        result = await UpdateContactUseCase(repository, self.clock)(
            UpdateContactCommand(
                self.tenant_id,
                self.actor_id,
                contact_id,
                "Іван",
                "Петренко",
                None,
            )
        )
        self.assertEqual(result.id, contact_id)
        repository.save.assert_not_awaited()
        await DeleteContactUseCase(repository)(
            DeleteContactCommand(self.tenant_id, contact_id)
        )
        repository.delete.assert_awaited_once_with(self.tenant_id, contact_id)

    async def test_company_create_update_and_delete(self):
        repository = SimpleNamespace(
            add=AsyncMock(), save=AsyncMock(), get=AsyncMock(), delete=AsyncMock()
        )
        company_id = CompanyIdVO.from_value(uuid4())
        await CreateCompanyUseCase(repository, self.clock)(
            CreateCompanyCommand(self.tenant_id, self.actor_id, company_id, "Acme")
        )
        entity = repository.add.await_args.args[1]
        repository.get.return_value = entity
        self.clock.value += timedelta(hours=1)
        result = await UpdateCompanyUseCase(repository, self.clock)(
            UpdateCompanyCommand(
                self.tenant_id, self.actor_id, company_id, "Acme Group"
            )
        )
        self.assertEqual(result.name, "Acme Group")
        repository.save.assert_awaited_once_with(self.tenant_id, entity)
        await DeleteCompanyUseCase(repository)(
            DeleteCompanyCommand(self.tenant_id, company_id)
        )
        repository.delete.assert_awaited_once_with(self.tenant_id, company_id)

    async def test_get_list_and_not_found_are_propagated(self):
        contact_repository = SimpleNamespace(get=AsyncMock(), list=AsyncMock())
        contact_id = ContactIdVO.from_value(uuid4())
        contact_repository.get.side_effect = ContactNotFoundError("missing")
        with self.assertRaises(ContactNotFoundError):
            await GetContactUseCase(contact_repository)(
                GetContactQuery(self.tenant_id, contact_id)
            )
        contact_page = SimpleNamespace(items=(), total=0, limit=25, offset=0)
        contact_repository.list.return_value = contact_page
        contact_query = ListContactsQuery(self.tenant_id, "ivan", 25, 0)
        self.assertIs(
            await ListContactsUseCase(contact_repository)(contact_query), contact_page
        )
        contact_repository.list.assert_awaited_once_with(contact_query)

        company_repository = SimpleNamespace(get=AsyncMock(), list=AsyncMock())
        company_id = CompanyIdVO.from_value(uuid4())
        company_repository.get.side_effect = CompanyNotFoundError("missing")
        with self.assertRaises(CompanyNotFoundError):
            await GetCompanyUseCase(company_repository)(
                GetCompanyQuery(self.tenant_id, company_id)
            )
        company_page = SimpleNamespace(items=(), total=0, limit=25, offset=0)
        company_repository.list.return_value = company_page
        company_query = ListCompaniesQuery(self.tenant_id, "acme", 25, 0)
        self.assertIs(
            await ListCompaniesUseCase(company_repository)(company_query), company_page
        )
        company_repository.list.assert_awaited_once_with(company_query)


class CrmPersistenceTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.now = datetime(2026, 9, 22, 10, 0, tzinfo=UTC)
        self.actor_id = uuid4()
        self.contact_id = uuid4()
        self.company_id = uuid4()

    def test_models_are_tenant_only_and_registered_for_migrations(self):
        self.assertNotIn("contacts", Base.metadata.tables)
        self.assertNotIn("companies", Base.metadata.tables)
        self.assertIs(
            TenantBase.metadata.tables["tenant.contacts"], ContactModel.__table__
        )
        self.assertIs(
            TenantBase.metadata.tables["tenant.companies"], CompanyModel.__table__
        )
        metadata = migration_metadata()
        self.assertIn("contacts", metadata.tables)
        self.assertIn("companies", metadata.tables)
        self.assertFalse({"contacts", "companies"} - managed_table_names(metadata))
        for table_name in ("contacts", "companies"):
            table = metadata.tables[table_name]
            self.assertNotIn("tenant_id", table.c)
            self.assertTrue(
                any(isinstance(item, CheckConstraint) for item in table.constraints)
            )
            self.assertTrue(any(isinstance(item, Index) for item in table.indexes))

    def test_explicit_row_mapping(self):
        contact = contact_entity(
            {
                "id": self.contact_id,
                "first_name": "Іван",
                "last_name": "Петренко",
                "middle_name": None,
                "created_at": self.now,
                "updated_at": self.now,
                "created_by": self.actor_id,
                "updated_by": self.actor_id,
            }
        )
        company = company_entity(
            {
                "id": self.company_id,
                "name": "Acme",
                "created_at": self.now,
                "updated_at": self.now,
                "created_by": self.actor_id,
                "updated_by": self.actor_id,
            }
        )
        self.assertEqual(contact.name.display_name, "Петренко Іван")
        self.assertEqual(company.name.value, "Acme")

    async def test_query_repositories_apply_search_pagination_and_tenant_scope(self):
        tenant_id = EntityIdVO.from_value(uuid4())
        contact_result = SimpleNamespace(
            mappings=lambda: [
                {
                    "id": self.contact_id,
                    "first_name": "Іван",
                    "last_name": "Петренко",
                    "middle_name": None,
                    "created_at": self.now,
                    "updated_at": self.now,
                    "created_by": self.actor_id,
                    "updated_by": self.actor_id,
                }
            ]
        )
        session = SimpleNamespace(
            scalar=AsyncMock(return_value=1),
            execute=AsyncMock(return_value=contact_result),
        )
        repository = SqlAlchemyContactRepository(session, TenantSchemaNaming("dnk_"))
        page = await repository.list(
            ListContactsQuery(tenant_id, q="Петренко Іван", limit=10, offset=20)
        )
        self.assertEqual((page.total, page.limit, page.offset), (1, 10, 20))
        statement = session.execute.await_args.args[0]
        self.assertIn("ORDER BY", str(statement))
        self.assertEqual(
            statement.get_execution_options()["schema_translate_map"]["tenant"],
            f"dnk_{tenant_id.uuid.hex}",
        )

        company_result = SimpleNamespace(
            mappings=lambda: [
                {
                    "id": self.company_id,
                    "name": "Acme",
                    "created_at": self.now,
                    "updated_at": self.now,
                    "created_by": self.actor_id,
                    "updated_by": self.actor_id,
                }
            ]
        )
        session.execute.return_value = company_result
        companies = SqlAlchemyCompanyRepository(session, TenantSchemaNaming("dnk_"))
        page = await companies.list(
            ListCompaniesQuery(tenant_id, q="acme", limit=25, offset=0)
        )
        self.assertEqual(page.items[0].name, "Acme")


if __name__ == "__main__":
    unittest.main()
