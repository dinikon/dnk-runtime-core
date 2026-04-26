from __future__ import annotations

import unittest
from datetime import UTC, datetime
from uuid import uuid4

from src.modules.custom_object.application import (
    CreateCustomRecordCommand,
    CreateCustomRecordUseCase,
    ListCustomRecordsQuery,
    ListCustomRecordsUseCase,
)
from src.modules.custom_object.domain import CustomObjectValidationError
from src.modules.runtime_data import FilterGroupSpec, FilterSpec, SortSpec
from src.modules.schema_registry.domain.object.value_object import RuntimeObjectIdVO
from src.modules.schema_registry.runtime import (
    RuntimeFieldDescriptor,
    RuntimeObjectDescriptor,
)
from src.modules.shared import TenantIdVO


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


def _descriptor() -> RuntimeObjectDescriptor:
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
        kind="custom",
    )


class _StoreStub:
    def __init__(self) -> None:
        self.calls = []

    async def resolve_descriptor(self, *, tenant_id, object_id):
        self.calls.append((tenant_id, object_id))
        return _descriptor()


class CustomObjectRecordUseCaseTests(unittest.IsolatedAsyncioTestCase):
    async def test_create_record_rejects_direct_system_field_write(self) -> None:
        tenant_id = TenantIdVO.from_value(uuid4())
        object_id = RuntimeObjectIdVO.from_value(uuid4())

        class CommandGatewaySpy:
            def __init__(self) -> None:
                self.insert_called = False

            async def insert(self, *, descriptor, payload):
                self.insert_called = True
                return {}

        gateway = CommandGatewaySpy()
        use_case = CreateCustomRecordUseCase(_StoreStub(), gateway)

        with self.assertRaises(CustomObjectValidationError):
            await use_case(
                CreateCustomRecordCommand(
                    tenant_id=tenant_id,
                    object_id=object_id,
                    values={"id": uuid4(), "name": "Acme"},
                )
            )

        self.assertFalse(gateway.insert_called)

    async def test_list_records_passes_filter_group_sort_and_page(self) -> None:
        tenant_id = TenantIdVO.from_value(uuid4())
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

        filter_group = FilterGroupSpec(
            logic="or",
            items=(
                FilterSpec(field="name", op="contains", value="Ac"),
                FilterSpec(field="status", op="eq", value="new"),
            ),
        )
        use_case = ListCustomRecordsUseCase(_StoreStub(), QueryGatewaySpy())

        result = await use_case(
            ListCustomRecordsQuery(
                tenant_id=tenant_id,
                object_id=object_id,
                filters=(filter_group,),
                sorting=(SortSpec(field="created_at", direction="desc"),),
                limit=25,
                offset=10,
            )
        )

        self.assertEqual(result[0].row_id, row_id)
        self.assertEqual(recorded["filters"], (filter_group,))
        self.assertEqual(recorded["sorting"][0].field, "created_at")
        self.assertEqual(recorded["page"].limit, 25)
        self.assertEqual(recorded["page"].offset, 10)


__all__ = ["CustomObjectRecordUseCaseTests"]
