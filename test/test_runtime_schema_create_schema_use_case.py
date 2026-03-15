from __future__ import annotations

import unittest
from datetime import UTC, datetime
from uuid import UUID, uuid4

from src.modules.runtime_schema.application.schema.dto import CreateSchemaCommandDTO
from src.modules.runtime_schema.application.schema.use_case import CreateSchemaUseCase
from src.modules.runtime_schema.domain.schema import (
    DataSourceEntity,
    InvalidSchemaTypeError,
)
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.shared.kernel.time.ports import ClockPort


class FixedClock(ClockPort):
    def __init__(self, value: datetime):
        self._value = value

    def now(self) -> datetime:
        return self._value


class FakeDataSourceRepository:
    def __init__(self) -> None:
        self.saved: DataSourceEntity | None = None

    async def add(self, entity: DataSourceEntity) -> DataSourceEntity:
        self.saved = entity
        return entity


class FakeDatabaseSchemaRepository:
    def __init__(self) -> None:
        self.created_schema_names: list[str] = []

    async def create_schema(self, schema_name: str) -> None:
        self.created_schema_names.append(schema_name)


class TestCreateSchemaUseCase(unittest.IsolatedAsyncioTestCase):
    async def test_execute_creates_schema_and_saves_entity(self) -> None:
        now = datetime(2026, 1, 1, tzinfo=UTC)
        data_source_repository = FakeDataSourceRepository()
        database_schema_repository = FakeDatabaseSchemaRepository()
        use_case = CreateSchemaUseCase(
            data_source_repository=data_source_repository,
            database_schema_repository=database_schema_repository,
            clock=FixedClock(now),
        )
        tenant_id = uuid4()

        result = await use_case.execute(
            CreateSchemaCommandDTO(
                tenant_id=str(tenant_id),
                schema_name="Tenant_Core",
                schema_type="postgres",
            )
        )

        assert data_source_repository.saved is not None
        self.assertEqual(database_schema_repository.created_schema_names, ["tenant_core"])
        self.assertEqual(str(data_source_repository.saved.tenant_id), str(tenant_id))
        self.assertEqual(str(data_source_repository.saved.schema_name), "tenant_core")
        self.assertEqual(data_source_repository.saved.type.value, "postgres")
        self.assertEqual(data_source_repository.saved.created_at, now)
        self.assertEqual(data_source_repository.saved.updated_at, now)
        self.assertEqual(result.schema_name, "tenant_core")
        self.assertEqual(result.schema_type, "postgres")
        self.assertEqual(result.tenant_id, str(tenant_id))
        UUID(result.schema_id)

    async def test_execute_raises_for_unsupported_schema_type(self) -> None:
        use_case = CreateSchemaUseCase(
            data_source_repository=FakeDataSourceRepository(),
            database_schema_repository=FakeDatabaseSchemaRepository(),
            clock=FixedClock(datetime(2026, 1, 1, tzinfo=UTC)),
        )
        tenant_id = EntityIdVO.new()

        with self.assertRaises(InvalidSchemaTypeError):
            await use_case.execute(
                CreateSchemaCommandDTO(
                    tenant_id=str(tenant_id),
                    schema_name="tenant_core",
                    schema_type="mysql",
                )
            )

