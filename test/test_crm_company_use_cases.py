from __future__ import annotations

import unittest
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from src.modules.crm.application.company.command import (
    CreateCompanyCommand,
    DeleteCompanyCommand,
    UpdateCompanyCommand,
)
from src.modules.crm.application.company.use_case import (
    CreateCompanyUseCase,
    DeleteCompanyUseCase,
    UpdateCompanyUseCase,
)
from src.modules.crm.domain.company.entity import CompanyEntity
from src.modules.crm.domain.company.error import CompanyNotFoundError
from src.modules.crm.domain.company.value_object import CompanyIdVO
from src.modules.shared import EntityIdVO


class CompanyUseCaseTests(unittest.IsolatedAsyncioTestCase):
    async def test_create_company_saves_entity_with_legal_name(self) -> None:
        tenant_id = EntityIdVO.from_value(uuid4())
        company_id = CompanyIdVO.from_value(uuid4())
        now = datetime.now(UTC)

        class ClockStub:
            def now(self):
                return now

        class RepositoryStub:
            saved_tenant_id = None
            saved_company = None

            async def load(self, *, tenant_id, company_id):
                raise AssertionError("load should not be called")

            async def save(self, *, tenant_id, company):
                self.saved_tenant_id = tenant_id
                self.saved_company = company
                return company

            async def delete(self, *, tenant_id, company_id):
                raise AssertionError("delete should not be called")

        repository = RepositoryStub()
        use_case = CreateCompanyUseCase(
            command_repository=repository,
            clock=ClockStub(),
        )

        result = await use_case(
            CreateCompanyCommand(
                tenant_id=tenant_id,
                company_id=company_id,
                legal_name="  Acme LLC  ",
            )
        )

        self.assertEqual(repository.saved_tenant_id, tenant_id)
        self.assertIsNotNone(repository.saved_company)
        assert repository.saved_company is not None
        self.assertEqual(repository.saved_company.id, company_id)
        self.assertEqual(repository.saved_company.created_at, now)
        self.assertEqual(repository.saved_company.updated_at, now)
        self.assertEqual(repository.saved_company.legal_name.value, "Acme LLC")
        self.assertEqual(result.legal_name, "Acme LLC")

    async def test_update_company_loads_updates_and_saves_entity(self) -> None:
        tenant_id = EntityIdVO.from_value(uuid4())
        company_id = CompanyIdVO.from_value(uuid4())
        now = datetime.now(UTC)
        updated_at = now + timedelta(minutes=1)
        company = CompanyEntity.create(
            id_=company_id,
            now=now,
            legal_name="Acme LLC",
        )

        class ClockStub:
            def now(self):
                return updated_at

        class RepositoryStub:
            loaded = False
            saved_company = None

            async def load(self, *, tenant_id, company_id):
                self.loaded = True
                return company

            async def save(self, *, tenant_id, company):
                self.saved_company = company
                return company

            async def delete(self, *, tenant_id, company_id):
                raise AssertionError("delete should not be called")

        repository = RepositoryStub()
        use_case = UpdateCompanyUseCase(
            command_repository=repository,
            clock=ClockStub(),
        )

        result = await use_case(
            UpdateCompanyCommand(
                tenant_id=tenant_id,
                company_id=company_id,
                legal_name="Acme Inc.",
            )
        )

        self.assertTrue(repository.loaded)
        self.assertIs(repository.saved_company, company)
        self.assertEqual(company.updated_at, updated_at)
        self.assertEqual(company.legal_name.value, "Acme Inc.")
        self.assertEqual(result.legal_name, "Acme Inc.")

    async def test_delete_company_loads_before_delete(self) -> None:
        tenant_id = EntityIdVO.from_value(uuid4())
        company_id = CompanyIdVO.from_value(uuid4())
        company = CompanyEntity.create(
            id_=company_id,
            now=datetime.now(UTC),
            legal_name="Acme LLC",
        )

        class RepositoryStub:
            deleted = False

            async def load(self, *, tenant_id, company_id):
                return company

            async def save(self, *, tenant_id, company):
                raise AssertionError("save should not be called")

            async def delete(self, *, tenant_id, company_id):
                self.deleted = True

        repository = RepositoryStub()
        use_case = DeleteCompanyUseCase(repository)

        await use_case(
            DeleteCompanyCommand(
                tenant_id=tenant_id,
                company_id=company_id,
            )
        )

        self.assertTrue(repository.deleted)

    async def test_delete_company_raises_when_company_is_missing(self) -> None:
        tenant_id = EntityIdVO.from_value(uuid4())
        company_id = CompanyIdVO.from_value(uuid4())

        class RepositoryStub:
            async def load(self, *, tenant_id, company_id):
                return None

            async def save(self, *, tenant_id, company):
                raise AssertionError("save should not be called")

            async def delete(self, *, tenant_id, company_id):
                raise AssertionError("delete should not be called")

        use_case = DeleteCompanyUseCase(RepositoryStub())

        with self.assertRaises(CompanyNotFoundError):
            await use_case(
                DeleteCompanyCommand(
                    tenant_id=tenant_id,
                    company_id=company_id,
                )
            )
