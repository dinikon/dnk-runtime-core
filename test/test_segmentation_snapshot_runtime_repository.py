from __future__ import annotations

import unittest
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from src.modules.runtime_data.application.models import (
    PageSpec,
    SortSpec,
    TypedFilterExpression,
    TypedFilterSpec,
)
from src.modules.schema_registry.runtime import (
    RuntimeFieldDescriptor,
    RuntimeObjectDescriptor,
)
from src.modules.segmentation.domain.segment_definition import SegmentIdVO
from src.modules.segmentation.domain.segment_snapshot import (
    SegmentSnapshot,
    SegmentSnapshotIdVO,
    SegmentSnapshotStatusVO,
)
from src.modules.segmentation.domain.segment_version import SegmentVersionIdVO
from src.modules.segmentation.infrastructure import (
    SegmentSnapshotMemberRuntimeRepository,
    SegmentSnapshotRuntimeRepository,
)
from src.modules.shared import EntityIdVO


def _field(name: str, type_code: str) -> RuntimeFieldDescriptor:
    return RuntimeFieldDescriptor(
        name=name,
        type_code=type_code,
        is_nullable=False,
        default_value=None,
        options={},
        settings={},
    )


def _descriptor(object_name: str) -> RuntimeObjectDescriptor:
    fields_by_object = {
        "segment_snapshot": (
            _field("id", "uuid"),
            _field("created_at", "datetime"),
            _field("updated_at", "datetime"),
            _field("segment_definition_id", "reference"),
            _field("segment_version_id", "reference"),
            _field("status", "select"),
            _field("member_count", "int"),
            _field("started_at", "datetime"),
            _field("completed_at", "datetime"),
            _field("error_code", "text"),
            _field("error_message", "text"),
        ),
        "segment_snapshot_member": (
            _field("id", "uuid"),
            _field("created_at", "datetime"),
            _field("segment_snapshot_id", "reference"),
            _field("contact_id", "uuid"),
            _field("position", "int"),
        ),
    }
    return RuntimeObjectDescriptor(
        schema_name="dnk_test",
        object_name=object_name,
        table_name=f"{object_name}s",
        pk="id",
        title_field="id",
        fields=fields_by_object[object_name],
        relations=(),
    )


class _ResolverStub:
    async def resolve(
        self,
        tenant_id: EntityIdVO,
        object_name: str,
    ) -> RuntimeObjectDescriptor:
        return _descriptor(object_name)


class _QueryGatewayStub:
    def __init__(self) -> None:
        self.rows_by_object: dict[str, list[Mapping[str, Any]]] = {}
        self.last_page: PageSpec | None = None
        self.last_sorting: Sequence[SortSpec] = ()

    async def get_by_id(
        self,
        *,
        descriptor: RuntimeObjectDescriptor,
        object_id: Any,
        fetch_plan=None,
    ) -> Mapping[str, Any] | None:
        for row in self.rows_by_object.get(descriptor.object_name, []):
            if row.get("id") == object_id:
                return row
        return None

    async def list(
        self,
        *,
        descriptor: RuntimeObjectDescriptor,
        filters: Sequence[TypedFilterExpression] = (),
        sorting: Sequence[SortSpec] = (),
        page: PageSpec | None = None,
        fetch_plan=None,
    ) -> list[Mapping[str, Any]]:
        self.last_page = page
        self.last_sorting = sorting
        rows = list(self.rows_by_object.get(descriptor.object_name, []))
        for expression in filters:
            if isinstance(expression, TypedFilterSpec) and expression.op == "eq":
                rows = [
                    row
                    for row in rows
                    if row.get(expression.field.name) == expression.value
                ]
        if page is not None:
            rows = rows[page.offset : page.offset + page.limit]
        return rows


class _CommandGatewayStub:
    def __init__(self, query_gateway: _QueryGatewayStub) -> None:
        self.query_gateway = query_gateway
        self.insert_payloads: list[Mapping[str, Any]] = []
        self.update_payloads: list[tuple[Any, Mapping[str, Any]]] = []
        self.deleted_ids: list[Any] = []

    async def acquire_advisory_xact_lock(self, key: str) -> None:
        return None

    async def insert(
        self,
        *,
        descriptor: RuntimeObjectDescriptor,
        payload: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        self.insert_payloads.append(dict(payload))
        now = datetime(2026, 5, 28, 12, 0, tzinfo=UTC)
        row = {
            "id": uuid4(),
            "created_at": now,
            "updated_at": now,
            **dict(payload),
        }
        self.query_gateway.rows_by_object.setdefault(descriptor.object_name, []).append(
            row
        )
        return row

    async def update(
        self,
        *,
        descriptor: RuntimeObjectDescriptor,
        object_id: Any,
        patch: Mapping[str, Any],
    ) -> Mapping[str, Any] | None:
        self.update_payloads.append((object_id, dict(patch)))
        rows = self.query_gateway.rows_by_object.get(descriptor.object_name, [])
        for index, row in enumerate(rows):
            if row.get("id") == object_id:
                new_row = dict(row)
                new_row.update(dict(patch))
                new_row["updated_at"] = datetime(2026, 5, 28, 12, 1, tzinfo=UTC)
                rows[index] = new_row
                return new_row
        return None

    async def delete(
        self,
        *,
        descriptor: RuntimeObjectDescriptor,
        object_id: Any,
    ) -> bool:
        self.deleted_ids.append(object_id)
        rows = self.query_gateway.rows_by_object.get(descriptor.object_name, [])
        self.query_gateway.rows_by_object[descriptor.object_name] = [
            row for row in rows if row.get("id") != object_id
        ]
        return True


class SegmentationSnapshotRuntimeRepositoryTests(unittest.IsolatedAsyncioTestCase):
    async def test_snapshot_repository_saves_maps_and_sorts(self) -> None:
        tenant_id = EntityIdVO.from_value(uuid4())
        segment_id = SegmentIdVO.from_value(uuid4())
        version_id = SegmentVersionIdVO.from_value(uuid4())
        snapshot_id = SegmentSnapshotIdVO.from_value(uuid4())
        query_gateway = _QueryGatewayStub()
        command_gateway = _CommandGatewayStub(query_gateway)
        repository = SegmentSnapshotRuntimeRepository(
            runtime_object_resolver=_ResolverStub(),
            runtime_command_gateway=command_gateway,
            runtime_query_gateway=query_gateway,
        )

        saved = await repository.save(
            tenant_id=tenant_id,
            snapshot=SegmentSnapshot.create(
                segment_snapshot_id=snapshot_id,
                segment_id=segment_id,
                segment_version_id=version_id,
            ),
        )
        dto = await repository.get(
            tenant_id=tenant_id,
            segment_snapshot_id=snapshot_id,
        )
        items = await repository.list(
            tenant_id=tenant_id,
            segment_id=segment_id,
            limit=10,
            offset=0,
        )

        self.assertEqual(saved.segment_snapshot_id, snapshot_id)
        self.assertEqual(dto.segment_version_id, version_id.uuid)
        self.assertEqual(items[0].id, snapshot_id.uuid)
        self.assertEqual(command_gateway.insert_payloads[0]["status"], "pending")
        self.assertEqual(
            query_gateway.last_sorting,
            (
                SortSpec(field="created_at", direction="desc"),
                SortSpec(field="id", direction="desc"),
            ),
        )

    async def test_snapshot_member_repository_adds_contact_only_payload(self) -> None:
        tenant_id = EntityIdVO.from_value(uuid4())
        snapshot_id = SegmentSnapshotIdVO.from_value(uuid4())
        contact_a = EntityIdVO.from_value(uuid4())
        contact_b = EntityIdVO.from_value(uuid4())
        query_gateway = _QueryGatewayStub()
        command_gateway = _CommandGatewayStub(query_gateway)
        repository = SegmentSnapshotMemberRuntimeRepository(
            runtime_object_resolver=_ResolverStub(),
            runtime_command_gateway=command_gateway,
            runtime_query_gateway=query_gateway,
        )

        count = await repository.add_members(
            tenant_id=tenant_id,
            segment_snapshot_id=snapshot_id,
            contact_ids=(contact_a, contact_b, contact_a),
            start_position=3,
        )

        self.assertEqual(count, 2)
        self.assertEqual(
            command_gateway.insert_payloads,
            [
                {
                    "segment_snapshot_id": snapshot_id.uuid,
                    "contact_id": contact_a.uuid,
                    "position": 3,
                },
                {
                    "segment_snapshot_id": snapshot_id.uuid,
                    "contact_id": contact_b.uuid,
                    "position": 4,
                },
            ],
        )
        self.assertNotIn("target_object_id", command_gateway.insert_payloads[0])

    async def test_snapshot_member_repository_lists_and_deletes_members(self) -> None:
        tenant_id = EntityIdVO.from_value(uuid4())
        snapshot_id = SegmentSnapshotIdVO.from_value(uuid4())
        member_id = uuid4()
        now = datetime(2026, 5, 28, 12, 0, tzinfo=UTC)
        query_gateway = _QueryGatewayStub()
        query_gateway.rows_by_object["segment_snapshot_member"] = [
            {
                "id": member_id,
                "created_at": now,
                "segment_snapshot_id": snapshot_id.uuid,
                "contact_id": uuid4(),
                "position": 0,
            }
        ]
        command_gateway = _CommandGatewayStub(query_gateway)
        repository = SegmentSnapshotMemberRuntimeRepository(
            runtime_object_resolver=_ResolverStub(),
            runtime_command_gateway=command_gateway,
            runtime_query_gateway=query_gateway,
        )

        items = await repository.list(
            tenant_id=tenant_id,
            segment_snapshot_id=snapshot_id,
            limit=10,
            offset=0,
        )
        list_page = query_gateway.last_page
        list_sorting = query_gateway.last_sorting
        await repository.delete_for_failed_snapshot(
            tenant_id=tenant_id,
            segment_snapshot_id=snapshot_id,
        )

        self.assertEqual(items[0].id, member_id)
        self.assertEqual(command_gateway.deleted_ids, [member_id])
        self.assertEqual(list_page, PageSpec(limit=10, offset=0))
        self.assertEqual(
            list_sorting,
            (
                SortSpec(field="position", direction="asc"),
                SortSpec(field="created_at", direction="asc"),
                SortSpec(field="id", direction="asc"),
            ),
        )


__all__ = ["SegmentationSnapshotRuntimeRepositoryTests"]
