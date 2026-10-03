"""Правила домена и сценариев Company."""

from dataclasses import FrozenInstanceError, replace
from datetime import UTC, datetime, timedelta
from typing import cast
import unittest
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

from sqlalchemy.engine import RowMapping

from src.modules.crm.application.company.command.create_company.command import (
    CreateCompanyCommand,
)
from src.modules.crm.application.company.command.create_company.handler import (
    CreateCompanyHandler,
)
from src.modules.crm.application.company.command.delete_company.command import (
    DeleteCompanyCommand,
)
from src.modules.crm.application.company.command.delete_company.handler import (
    DeleteCompanyHandler,
)
from src.modules.crm.application.company.command.update_company.command import (
    UpdateCompanyCommand,
)
from src.modules.crm.application.company.command.update_company.handler import (
    UpdateCompanyHandler,
)
from src.modules.crm.application.company.query.get_company.handler import (
    GetCompanyHandler,
)
from src.modules.crm.application.company.query.get_company.query import GetCompanyQuery
from src.modules.crm.application.company.query.list_companies.handler import (
    ListCompaniesHandler,
)
from src.modules.crm.application.company.query.list_companies.query import (
    ListCompaniesQuery,
)
from src.modules.crm.domain.company.aggregate import CompanyEntity
from src.modules.crm.domain.company.error import (
    CompanyNotFoundError,
    InvalidCompanyLegalNameError,
)
from src.modules.crm.domain.company.value_object.identifier import CompanyIdVO
from src.modules.crm.domain.company.value_object.legal_name import CompanyLegalNameVO
from src.modules.crm.infrastructure.company.persistence.mapper import CompanyMapper
from src.modules.crm.infrastructure.company.persistence.query_repository import (
    SqlAlchemyCompanyQueryRepository,
)
from src.modules.crm.infrastructure.company.persistence.repository import (
    SqlAlchemyCompanyRepository,
)
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


class CompanyDomainTests(unittest.TestCase):
    def test_legal_name_is_normalized_and_immutable(self):
        name = CompanyLegalNameVO("  ACME  Group \t")
        self.assertEqual(name.value, "ACME  Group")
        with self.assertRaises(FrozenInstanceError):
            name.value = "Other"
        self.assertEqual(len(CompanyLegalNameVO(" " + "a" * 255 + " ").value), 255)

    def test_invalid_type_empty_and_too_long_are_rejected(self):
        for value in (None, 1, False, [], b"name", "", " \n", "x" * 256):
            with (
                self.subTest(value=value),
                self.assertRaises(InvalidCompanyLegalNameError),
            ):
                CompanyLegalNameVO(value)

    def test_create_and_update_preserve_audit_on_noop(self):
        actor, editor = EntityIdVO(uuid4()), EntityIdVO(uuid4())
        now = datetime(2026, 10, 3, tzinfo=UTC)
        later = now + timedelta(days=1)
        identifier = CompanyIdVO(uuid4())
        company = CompanyEntity.create(
            company_id=identifier, legal_name=" ACME ", actor_id=actor, now=now
        )
        self.assertEqual(company.id, identifier)
        self.assertEqual(company.legal_name, CompanyLegalNameVO("ACME"))
        self.assertEqual((company.created_at, company.updated_at), (now, now))
        self.assertEqual((company.created_by, company.updated_by), (actor, actor))
        self.assertFalse(company.update(legal_name="ACME ", actor_id=editor, now=later))
        self.assertEqual((company.updated_at, company.updated_by), (now, actor))
        with self.assertRaises(InvalidCompanyLegalNameError):
            company.update(legal_name=" ", actor_id=editor, now=later)
        self.assertEqual(company.legal_name.value, "ACME")
        self.assertTrue(company.update(legal_name=" New ", actor_id=editor, now=later))
        self.assertEqual((company.updated_at, company.updated_by), (later, editor))
        self.assertEqual((company.created_at, company.created_by), (now, actor))


class CompanyHandlerTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.identifier, self.actor = uuid4(), EntityIdVO(uuid4())
        self.now = datetime(2026, 10, 3, tzinfo=UTC)
        self.company = CompanyEntity.create(
            company_id=CompanyIdVO(self.identifier),
            legal_name="Old",
            actor_id=self.actor,
            now=self.now,
        )
        self.repository = Mock(
            add=AsyncMock(),
            get_for_update=AsyncMock(return_value=self.company),
            save=AsyncMock(),
            delete=AsyncMock(),
        )
        self.clock = Mock(now=Mock(return_value=self.now))
        self.uuid = Mock(new=Mock(return_value=self.identifier))

    async def test_create_returns_normalized_data_and_saves_once(self):
        handler = CreateCompanyHandler(self.repository, self.clock, self.uuid)
        command = CreateCompanyCommand(self.actor, " New ")
        result = await handler.execute(command)
        self.repository.add.assert_awaited_once()
        self.clock.now.assert_called_once_with()
        self.uuid.new.assert_called_once_with()
        self.assertEqual((result.id, result.legal_name), (self.identifier, "New"))
        self.assertEqual((result.created_by, result.updated_by), (self.actor.uuid,) * 2)
        self.assertEqual((result.created_at, result.updated_at), (self.now,) * 2)
        self.repository.add.reset_mock()
        with self.assertRaises(InvalidCompanyLegalNameError):
            await handler.execute(replace(command, legal_name=" "))
        self.repository.add.assert_not_awaited()

    async def test_update_changes_once_and_unchanged_value_does_not_save(self):
        handler = UpdateCompanyHandler(self.repository, self.clock)
        command = UpdateCompanyCommand(self.company.id, self.actor, " New ")
        result = await handler.execute(command)
        self.assertEqual(result.legal_name, "New")
        self.repository.save.assert_awaited_once_with(self.company)
        await handler.execute(command)
        self.repository.save.assert_awaited_once()
        self.assertEqual(self.repository.get_for_update.await_count, 2)

    async def test_delete_uses_locked_aggregate(self):
        await DeleteCompanyHandler(self.repository).execute(
            DeleteCompanyCommand(self.company.id)
        )
        self.repository.delete.assert_awaited_once_with(self.company)

    async def test_absence_and_storage_errors_propagate(self):
        self.repository.get_for_update.return_value = None
        with self.assertRaises(CompanyNotFoundError):
            await UpdateCompanyHandler(self.repository, self.clock).execute(
                UpdateCompanyCommand(self.company.id, self.actor, "New")
            )
        with self.assertRaises(CompanyNotFoundError):
            await DeleteCompanyHandler(self.repository).execute(
                DeleteCompanyCommand(self.company.id)
            )
        self.repository.add.side_effect = RuntimeError("storage")
        with self.assertRaises(RuntimeError):
            await CreateCompanyHandler(self.repository, self.clock, self.uuid).execute(
                CreateCompanyCommand(self.actor, "New")
            )

    async def test_queries_use_projection_repository(self):
        projection = Mock(
            get_details=AsyncMock(return_value=None),
            list_details=AsyncMock(return_value=[]),
        )
        query = GetCompanyQuery(self.company.id)
        with self.assertRaises(CompanyNotFoundError):
            await GetCompanyHandler(projection).execute(query)
        projection.get_details.assert_awaited_once_with(company_id=self.company.id)
        result = await ListCompaniesHandler(projection).execute(ListCompaniesQuery())
        self.assertEqual(result.companies, ())


class CompanyPersistenceTests(unittest.IsolatedAsyncioTestCase):
    async def test_write_hydrates_vo_and_locks_without_schema_selection(self):
        now, actor, identifier = datetime(2026, 10, 3, tzinfo=UTC), uuid4(), uuid4()
        row = dict(
            id=identifier,
            legal_name="Stored",
            created_at=now,
            updated_at=now,
            created_by=actor,
            updated_by=actor,
        )
        self.assertEqual(
            CompanyMapper.to_entity(cast(RowMapping, row)).legal_name.value, "Stored"
        )
        result = Mock()
        result.mappings.return_value.one_or_none.return_value = row
        session = Mock(execute=AsyncMock(return_value=result))
        repository = SqlAlchemyCompanyRepository(session)
        company = await repository.get_for_update(CompanyIdVO(identifier))
        self.assertIsNotNone(company)
        self.assertIsInstance(company.legal_name, CompanyLegalNameVO)
        statement = session.execute.await_args.args[0]
        self.assertIn("FOR UPDATE", str(statement.compile()))
        self.assertNotIn("schema_translate_map", statement.get_execution_options())
        session.execute.reset_mock()
        await repository.save(company)
        statement = session.execute.await_args.args[0]
        self.assertTrue(str(statement.compile()).startswith("UPDATE "))
        self.assertNotIn("schema_translate_map", statement.get_execution_options())

    async def test_query_projection_and_stable_order(self):
        now, actor, identifier = datetime(2026, 10, 3, tzinfo=UTC), uuid4(), uuid4()
        row = dict(
            id=identifier,
            legal_name="Stored",
            created_at=now,
            updated_at=now,
            created_by=actor,
            updated_by=actor,
        )
        result = Mock()
        result.mappings.return_value.one_or_none.return_value = row
        result.mappings.return_value.all.return_value = [row]
        session = Mock(execute=AsyncMock(return_value=result))
        repository = SqlAlchemyCompanyQueryRepository(session)
        details = await repository.get_details(company_id=CompanyIdVO(identifier))
        self.assertEqual(details.legal_name, "Stored")
        statement = session.execute.await_args.args[0]
        self.assertEqual(set(statement.selected_columns.keys()), set(row))
        self.assertNotIn("FOR UPDATE", str(statement.compile()))
        self.assertNotIn("schema_translate_map", statement.get_execution_options())
        listed = await repository.list_details()
        self.assertEqual(listed, [details])
        self.assertIn("ORDER BY", str(session.execute.await_args.args[0].compile()))
