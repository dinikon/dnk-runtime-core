from __future__ import annotations

import unittest
from datetime import UTC, datetime
from uuid import uuid4

from src.modules.custom_object.application.record.command import (
    CreateCustomRecordCommand,
)
from src.modules.custom_object.application.record.query import (
    ListCustomRecordsQuery,
)
from src.modules.custom_object.application.record.use_case import (
    CreateCustomRecordUseCase,
    ListCustomRecordsUseCase,
)
from src.modules.custom_object.domain import CustomObjectValidationError
from src.modules.custom_object.infrastructure import CustomRecordRuntimeRepository
from src.modules.runtime_data.application.models import TypedFilterGroupSpec
from src.modules.schema_registry.domain.object.value_object import RuntimeObjectIdVO
from src.modules.schema_registry.runtime import (
    RuntimeFieldDescriptor,
    RuntimeObjectDescriptor,
)
from src.modules.shared import EntityIdVO


def _field(
    name: str, type_code: str, *, kind: str = "custom", is_nullable: bool = True
):
    return RuntimeFieldDescriptor(
        name=name,
        type_code=type_code,
        is_nullable=is_nullable,
        default_value=None,
        options={},
        settings={},
        kind=kind,
    )


def _descriptor(*, kind: str = "custom") -> RuntimeObjectDescriptor:
    return RuntimeObjectDescriptor(
        schema_name="dnk_test",
        object_name="deal",
        table_name="deals",
        pk="id",
        title_field="id",
        fields=(
            _field("id", "uuid", kind="system", is_nullable=False),
            _field("created_at", "datetime", kind="system", is_nullable=False),
            _field("updated_at", "datetime", kind="system", is_nullable=False),
            _field("name", "text", is_nullable=False),
            _field("status", "select", is_nullable=False),
        ),
        relations=(),
        kind=kind,
    )


class _RuntimeObjectResolverStub:
    def __init__(self, descriptor: RuntimeObjectDescriptor | None = None) -> None:
        self.descriptor = descriptor or _descriptor()
        self.calls = []

    async def resolve(self, tenant_id, object_name):
        raise AssertionError(
            "custom_object record repository must resolve by object_id"
        )

    async def resolve_by_id(self, tenant_id, object_id):
        self.calls.append((tenant_id, object_id))
        return self.descriptor


def _repository(
    *,
    command_gateway=object(),
    query_gateway=object(),
    descriptor: RuntimeObjectDescriptor | None = None,
) -> tuple[CustomRecordRuntimeRepository, _RuntimeObjectResolverStub]:
    resolver = _RuntimeObjectResolverStub(descriptor)
    return (
        CustomRecordRuntimeRepository(
            runtime_object_resolver=resolver,
            command_gateway=command_gateway,
            query_gateway=query_gateway,
        ),
        resolver,
    )


class CustomObjectRecordUseCaseTests(unittest.IsolatedAsyncioTestCase):
    async def test_create_record_rejects_direct_system_field_write(self) -> None:
        tenant_id = EntityIdVO.from_value(uuid4())
        object_id = RuntimeObjectIdVO.from_value(uuid4())

        class CommandGatewaySpy:
            def __init__(self) -> None:
                self.insert_called = False

            async def insert(self, *, descriptor, payload):
                self.insert_called = True
                return {}

        gateway = CommandGatewaySpy()
        repository, resolver = _repository(
            command_gateway=gateway,
            query_gateway=object(),
        )
        use_case = CreateCustomRecordUseCase(repository)

        with self.assertRaises(CustomObjectValidationError):
            await use_case(
                CreateCustomRecordCommand(
                    tenant_id=tenant_id,
                    object_id=object_id,
                    values={"id": uuid4(), "name": "Acme"},
                )
            )

        self.assertFalse(gateway.insert_called)
        self.assertEqual(resolver.calls, [(tenant_id, object_id)])

    async def test_list_records_passes_filter_group_sort_and_page(self) -> None:
        tenant_id = EntityIdVO.from_value(uuid4())
        object_id = RuntimeObjectIdVO.from_value(uuid4())
        row_id = uuid4()
        now = datetime.now(UTC)
        recorded = {}

        class QueryGatewaySpy:
            async def get_by_id(self, *, descriptor, object_id, fetch_plan=None):
                return None

            async def list(
                self, *, descriptor, filters=(), sorting=(), page=None, fetch_plan=None
            ):
                recorded["filters"] = filters
                recorded["sorting"] = sorting
                recorded["page"] = page
                return [
                    {
                        "id": row_id,
                        "created_at": now,
                        "updated_at": now,
                        "name": "Acme",
                        "status": "new",
                    }
                ]

        filter_dsl = {
            "or": [
                {"field": "name", "op": "contains", "value": "Ac"},
                {"field": "status", "op": "eq", "value": "new"},
            ]
        }
        repository, _resolver = _repository(
            command_gateway=object(),
            query_gateway=QueryGatewaySpy(),
        )
        use_case = ListCustomRecordsUseCase(repository)

        result = await use_case(
            ListCustomRecordsQuery(
                tenant_id=tenant_id,
                object_id=object_id,
                filter_dsl=filter_dsl,
                sort_dsl=[{"field": "created_at", "direction": "desc"}],
                limit=25,
                offset=10,
            )
        )

        self.assertEqual(result[0].row_id, row_id)
        self.assertIsInstance(recorded["filters"][0], TypedFilterGroupSpec)
        self.assertEqual(recorded["filters"][0].logic, "or")
        self.assertEqual(recorded["filters"][0].items[0].field.name, "name")
        self.assertEqual(recorded["filters"][0].items[0].op, "contains")
        self.assertEqual(recorded["filters"][0].items[1].field.name, "status")
        self.assertEqual(recorded["filters"][0].items[1].op, "eq")
        self.assertEqual(recorded["sorting"][0].field, "created_at")
        self.assertEqual(recorded["page"].limit, 25)
        self.assertEqual(recorded["page"].offset, 10)

    async def test_record_operations_reject_non_custom_descriptor(self) -> None:
        tenant_id = EntityIdVO.from_value(uuid4())
        object_id = RuntimeObjectIdVO.from_value(uuid4())

        class CommandGatewaySpy:
            def __init__(self) -> None:
                self.insert_called = False

            async def insert(self, *, descriptor, payload):
                self.insert_called = True
                return {}

        gateway = CommandGatewaySpy()
        repository, _resolver = _repository(
            command_gateway=gateway,
            query_gateway=object(),
            descriptor=_descriptor(kind="standard"),
        )
        use_case = CreateCustomRecordUseCase(repository)

        with self.assertRaises(CustomObjectValidationError):
            await use_case(
                CreateCustomRecordCommand(
                    tenant_id=tenant_id,
                    object_id=object_id,
                    values={"name": "Acme"},
                )
            )

        self.assertFalse(gateway.insert_called)


__all__ = ["CustomObjectRecordUseCaseTests"]
