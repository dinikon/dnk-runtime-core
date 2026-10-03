"""Чтение проекции Contact без восстановления доменной модели."""

from dataclasses import asdict
from datetime import UTC, datetime, timedelta
import unittest
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

from src.modules.crm.application.contact.query.get_contact.dto import ContactDetailsDTO
from src.modules.crm.application.contact.query.get_contact.handler import (
    GetContactHandler,
)
from src.modules.crm.application.contact.query.get_contact.query import GetContactQuery
from src.modules.crm.domain.contact.error import ContactNotFoundError
from src.modules.crm.domain.contact.value_object.identifier import ContactIdVO
from src.modules.crm.infrastructure.contact.persistence.query_mapper import (
    ContactQueryMapper,
)
from src.modules.crm.infrastructure.contact.persistence.query_repository import (
    SqlAlchemyContactQueryRepository,
)
from src.modules.tenancy.application.tenant.tenant_schema_naming import (
    TenantSchemaNaming,
)
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


def contact_row():
    now = datetime(2026, 9, 30, tzinfo=UTC)
    return dict(
        id=uuid4(),
        first_name="  Legacy  Name ",
        last_name=None,
        middle_name=None,
        created_at=now,
        updated_at=now + timedelta(days=1),
        created_by=uuid4(),
        updated_by=uuid4(),
    )


class ContactQueryMapperTests(unittest.TestCase):
    def test_preserves_all_persisted_values_without_domain_validation(self):
        for last_name, middle_name in ((None, None), (" Last ", " Middle ")):
            row = contact_row() | dict(last_name=last_name, middle_name=middle_name)
            with (
                self.subTest(last_name=last_name),
                patch(
                    "src.modules.crm.domain.contact.aggregate.ContactEntity.create",
                    side_effect=AssertionError("No aggregate on read"),
                ),
                patch(
                    "src.modules.crm.domain.contact.value_object.name.ContactNameVO.__post_init__",
                    side_effect=AssertionError("No name VO on read"),
                ),
            ):
                self.assertEqual(asdict(ContactQueryMapper.to_details(row)), row)


class GetContactHandlerTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.query = GetContactQuery(EntityIdVO(uuid4()), ContactIdVO(uuid4()))
        self.repository = Mock(get_details=AsyncMock())
        self.handler = GetContactHandler(self.repository)

    async def test_returns_same_projection_and_passes_typed_scope(self):
        dto = ContactDetailsDTO(**contact_row())
        self.repository.get_details.return_value = dto
        self.assertIs(await self.handler.execute(self.query), dto)
        self.repository.get_details.assert_awaited_once_with(
            tenant_id=self.query.tenant_id, contact_id=self.query.contact_id
        )

    async def test_absence_is_contact_not_found(self):
        self.repository.get_details.return_value = None
        with self.assertRaises(ContactNotFoundError):
            await self.handler.execute(self.query)

    async def test_storage_errors_propagate(self):
        error = RuntimeError("storage failure")
        self.repository.get_details.side_effect = error
        with self.assertRaises(RuntimeError) as caught:
            await self.handler.execute(self.query)
        self.assertIs(caught.exception, error)


class ContactQueryRepositoryTests(unittest.IsolatedAsyncioTestCase):
    async def test_reads_only_requested_columns_and_scope_without_lock(self):
        row = contact_row()
        result = Mock()
        result.mappings.return_value.one_or_none.return_value = row
        session = Mock(execute=AsyncMock(return_value=result))
        naming = TenantSchemaNaming("tenant_")
        repository = SqlAlchemyContactQueryRepository(session, naming)
        tenant, identifier = EntityIdVO(uuid4()), ContactIdVO(row["id"])
        self.assertEqual(
            asdict(
                await repository.get_details(tenant_id=tenant, contact_id=identifier)
            ),
            row,
        )
        session.execute.assert_awaited_once()
        statement = session.execute.await_args.args[0]
        sql = str(statement.compile())
        self.assertTrue(sql.startswith("SELECT "))
        self.assertNotIn("FOR UPDATE", sql)
        self.assertNotIn("JOIN", sql)
        self.assertEqual(set(statement.selected_columns.keys()), set(row))
        self.assertEqual(statement.compile().params, {"id_1": row["id"]})
        self.assertEqual(
            statement.get_execution_options()["schema_translate_map"],
            {"tenant": naming.schema_name(tenant)},
        )

    async def test_missing_row_is_none_without_mapping(self):
        result = Mock()
        result.mappings.return_value.one_or_none.return_value = None
        repository = SqlAlchemyContactQueryRepository(
            Mock(execute=AsyncMock(return_value=result)), TenantSchemaNaming("tenant_")
        )
        with patch.object(
            ContactQueryMapper, "to_details", side_effect=AssertionError("Missing row")
        ):
            self.assertIsNone(
                await repository.get_details(
                    tenant_id=EntityIdVO(uuid4()), contact_id=ContactIdVO(uuid4())
                )
            )
