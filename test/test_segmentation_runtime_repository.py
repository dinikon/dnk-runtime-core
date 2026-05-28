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
from src.modules.runtime_data.domain.error import RuntimeDataPersistenceError
from src.modules.schema_registry.runtime import (
    RuntimeFieldDescriptor,
    RuntimeObjectDescriptor,
)
from src.modules.segmentation.domain.segment_definition import (
    SegmentDefinition,
    SegmentIdVO,
    SegmentKindVO,
    SegmentStatusVO,
)
from src.modules.segmentation.domain.segment_static_member import (
    SegmentStaticMember,
    SegmentStaticMemberIdVO,
    SegmentStaticMemberSourceTypeVO,
)
from src.modules.segmentation.domain.segment_version import (
    SegmentVersion,
    SegmentVersionIdVO,
    SegmentVersionStatusVO,
)
from src.modules.segmentation.infrastructure import (
    RuntimeContactLookupAdapter,
    SegmentDefinitionRuntimeRepository,
    SegmentStaticMemberRuntimeRepository,
    SegmentVersionRuntimeRepository,
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
        "segment_static_member": (
            _field("id", "uuid"),
            _field("created_at", "datetime"),
            _field("updated_at", "datetime"),
            _field("segment_definition_id", "reference"),
            _field("contact_id", "uuid"),
            _field("source_type", "select"),
            _field("metadata", "json"),
        ),
        "segment_definition": (
            _field("id", "uuid"),
            _field("created_at", "datetime"),
            _field("updated_at", "datetime"),
            _field("name", "text"),
            _field("description", "text"),
            _field("segment_kind", "select"),
            _field("status", "select"),
            _field("archived_at", "datetime"),
        ),
        "segment_version": (
            _field("id", "uuid"),
            _field("created_at", "datetime"),
            _field("updated_at", "datetime"),
            _field("segment_definition_id", "reference"),
            _field("version_number", "int"),
            _field("status", "select"),
            _field("config", "json"),
            _field("config_checksum", "text"),
            _field("activated_at", "datetime"),
            _field("archived_at", "datetime"),
        ),
        "contact": (
            _field("id", "uuid"),
            _field("first_name", "text"),
            _field("last_name", "text"),
            _field("middle_name", "text"),
            _field("status", "text"),
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
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    async def resolve(
        self,
        tenant_id: EntityIdVO,
        object_name: str,
    ) -> RuntimeObjectDescriptor:
        self.calls.append((str(tenant_id), object_name))
        return _descriptor(object_name)


class _CommandGatewayStub:
    def __init__(self, query_gateway: "_QueryGatewayStub") -> None:
        self.query_gateway = query_gateway
        self.events: list[str] = query_gateway.events
        self.locks: list[str] = []
        self.insert_payloads: list[Mapping[str, Any]] = []
        self.update_payloads: list[tuple[Any, Mapping[str, Any]]] = []
        self.update_where_payloads: list[
            tuple[Sequence[TypedFilterExpression], Mapping[str, Any]]
        ] = []
        self.deleted_ids: list[Any] = []
        self.fail_insert_with_row: Mapping[str, Any] | None = None

    async def acquire_advisory_xact_lock(self, key: str) -> None:
        self.locks.append(key)
        self.events.append(f"lock:{key}")

    async def insert(
        self,
        *,
        descriptor: RuntimeObjectDescriptor,
        payload: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        self.insert_payloads.append(dict(payload))
        if self.fail_insert_with_row is not None:
            self.query_gateway.rows_by_object.setdefault(
                descriptor.object_name, []
            ).append(dict(self.fail_insert_with_row))
            raise RuntimeDataPersistenceError("duplicate")
        now = datetime(2026, 5, 28, 12, 0, tzinfo=UTC)
        row = {
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
        before = len(rows)
        self.query_gateway.rows_by_object[descriptor.object_name] = [
            row for row in rows if row.get("id") != object_id
        ]
        return len(self.query_gateway.rows_by_object[descriptor.object_name]) != before

    async def update_where(
        self,
        *,
        descriptor: RuntimeObjectDescriptor,
        filters: Sequence[TypedFilterExpression],
        patch: Mapping[str, Any],
    ) -> list[Mapping[str, Any]]:
        self.update_where_payloads.append((filters, dict(patch)))
        rows = self.query_gateway.rows_by_object.get(descriptor.object_name, [])
        updated: list[Mapping[str, Any]] = []
        for index, row in enumerate(rows):
            matches = True
            for expression in filters:
                if (
                    isinstance(expression, TypedFilterSpec)
                    and expression.op == "eq"
                    and row.get(expression.field.name) != expression.value
                ):
                    matches = False
            if matches:
                new_row = dict(row)
                new_row.update(dict(patch))
                new_row["updated_at"] = datetime(2026, 5, 28, 12, 1, tzinfo=UTC)
                rows[index] = new_row
                updated.append(new_row)
        return updated


class _QueryGatewayStub:
    def __init__(self) -> None:
        self.rows_by_object: dict[str, list[Mapping[str, Any]]] = {}
        self.events: list[str] = []
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
        self.events.append(f"list:{descriptor.object_name}")
        self.last_page = page
        self.last_sorting = sorting
        rows = list(self.rows_by_object.get(descriptor.object_name, []))
        for expression in filters:
            if isinstance(expression, TypedFilterSpec):
                if expression.op == "eq":
                    rows = [
                        row
                        for row in rows
                        if row.get(expression.field.name) == expression.value
                    ]
                elif expression.op == "in":
                    values = set(expression.value)
                    rows = [
                        row for row in rows if row.get(expression.field.name) in values
                    ]
        if page is not None:
            rows = rows[page.offset : page.offset + page.limit]
        return rows


class SegmentationRuntimeRepositoryTests(unittest.IsolatedAsyncioTestCase):
    async def test_static_member_add_locks_before_lookup_and_inserts_payload(
        self,
    ) -> None:
        tenant_id = EntityIdVO.from_value(uuid4())
        segment_id = SegmentIdVO.from_value(uuid4())
        contact_id = EntityIdVO.from_value(uuid4())
        query_gateway = _QueryGatewayStub()
        command_gateway = _CommandGatewayStub(query_gateway)
        repository = SegmentStaticMemberRuntimeRepository(
            runtime_object_resolver=_ResolverStub(),
            runtime_command_gateway=command_gateway,
            runtime_query_gateway=query_gateway,
        )
        member = SegmentStaticMember(
            segment_static_member_id=SegmentStaticMemberIdVO.from_value(uuid4()),
            segment_id=segment_id,
            contact_id=contact_id,
            source_type=SegmentStaticMemberSourceTypeVO.API,
            metadata={"source": "test"},
        )

        saved = await repository.add(tenant_id=tenant_id, member=member)

        self.assertEqual(
            saved.segment_static_member_id, member.segment_static_member_id
        )
        self.assertEqual(query_gateway.events[0].split(":")[0], "lock")
        self.assertEqual(query_gateway.events[1], "list:segment_static_member")
        self.assertIn(str(tenant_id.uuid), command_gateway.locks[0])
        self.assertEqual(
            command_gateway.insert_payloads[0]["segment_definition_id"],
            segment_id.uuid,
        )
        self.assertEqual(
            command_gateway.insert_payloads[0]["contact_id"], contact_id.uuid
        )

    async def test_static_member_add_rereads_existing_after_unique_race(self) -> None:
        tenant_id = EntityIdVO.from_value(uuid4())
        segment_id = SegmentIdVO.from_value(uuid4())
        contact_id = EntityIdVO.from_value(uuid4())
        existing_id = uuid4()
        now = datetime(2026, 5, 28, 12, 0, tzinfo=UTC)
        query_gateway = _QueryGatewayStub()
        command_gateway = _CommandGatewayStub(query_gateway)
        command_gateway.fail_insert_with_row = {
            "id": existing_id,
            "created_at": now,
            "updated_at": now,
            "segment_definition_id": segment_id.uuid,
            "contact_id": contact_id.uuid,
            "source_type": "manual",
            "metadata": None,
        }
        repository = SegmentStaticMemberRuntimeRepository(
            runtime_object_resolver=_ResolverStub(),
            runtime_command_gateway=command_gateway,
            runtime_query_gateway=query_gateway,
        )

        saved = await repository.add(
            tenant_id=tenant_id,
            member=SegmentStaticMember(
                segment_static_member_id=SegmentStaticMemberIdVO.from_value(uuid4()),
                segment_id=segment_id,
                contact_id=contact_id,
                source_type=SegmentStaticMemberSourceTypeVO.MANUAL,
            ),
        )

        self.assertEqual(saved.segment_static_member_id.uuid, existing_id)
        self.assertEqual(
            command_gateway.insert_payloads[0]["contact_id"], contact_id.uuid
        )

    async def test_static_member_remove_deletes_by_existing_row_id(self) -> None:
        tenant_id = EntityIdVO.from_value(uuid4())
        segment_id = SegmentIdVO.from_value(uuid4())
        contact_id = EntityIdVO.from_value(uuid4())
        member_id = uuid4()
        now = datetime(2026, 5, 28, 12, 0, tzinfo=UTC)
        query_gateway = _QueryGatewayStub()
        query_gateway.rows_by_object["segment_static_member"] = [
            {
                "id": member_id,
                "created_at": now,
                "updated_at": now,
                "segment_definition_id": segment_id.uuid,
                "contact_id": contact_id.uuid,
                "source_type": "manual",
                "metadata": None,
            }
        ]
        command_gateway = _CommandGatewayStub(query_gateway)
        repository = SegmentStaticMemberRuntimeRepository(
            runtime_object_resolver=_ResolverStub(),
            runtime_command_gateway=command_gateway,
            runtime_query_gateway=query_gateway,
        )

        removed = await repository.remove(
            tenant_id=tenant_id,
            segment_id=segment_id,
            contact_id=contact_id,
        )

        self.assertTrue(removed)
        self.assertEqual(command_gateway.deleted_ids, [member_id])

    async def test_static_member_list_uses_page_sorting_and_maps_dto(self) -> None:
        tenant_id = EntityIdVO.from_value(uuid4())
        segment_id = SegmentIdVO.from_value(uuid4())
        now = datetime(2026, 5, 28, 12, 0, tzinfo=UTC)
        query_gateway = _QueryGatewayStub()
        query_gateway.rows_by_object["segment_static_member"] = [
            {
                "id": uuid4(),
                "created_at": now,
                "updated_at": now,
                "segment_definition_id": segment_id.uuid,
                "contact_id": uuid4(),
                "source_type": "api",
                "metadata": {"batch": 1},
            }
        ]
        repository = SegmentStaticMemberRuntimeRepository(
            runtime_object_resolver=_ResolverStub(),
            runtime_command_gateway=_CommandGatewayStub(query_gateway),
            runtime_query_gateway=query_gateway,
        )

        result = await repository.list(
            tenant_id=tenant_id,
            segment_id=segment_id,
            limit=10,
            offset=0,
        )

        self.assertEqual(result[0].segment_id, segment_id.uuid)
        self.assertEqual(result[0].metadata, {"batch": 1})
        self.assertEqual(query_gateway.last_page, PageSpec(limit=10, offset=0))
        self.assertEqual(
            query_gateway.last_sorting,
            (
                SortSpec(field="created_at", direction="asc"),
                SortSpec(field="id", direction="asc"),
            ),
        )

    async def test_segment_definition_repository_load_maps_entity(self) -> None:
        tenant_id = EntityIdVO.from_value(uuid4())
        segment_id = SegmentIdVO.from_value(uuid4())
        query_gateway = _QueryGatewayStub()
        query_gateway.rows_by_object["segment_definition"] = [
            {
                "id": segment_id.uuid,
                "name": "VIP",
                "description": None,
                "segment_kind": "static",
                "status": "active",
                "archived_at": None,
            }
        ]
        repository = SegmentDefinitionRuntimeRepository(
            runtime_object_resolver=_ResolverStub(),
            runtime_command_gateway=_CommandGatewayStub(query_gateway),
            runtime_query_gateway=query_gateway,
        )

        segment = await repository.load(tenant_id=tenant_id, segment_id=segment_id)

        self.assertEqual(segment.segment_kind, SegmentKindVO.STATIC)
        self.assertEqual(segment.status, SegmentStatusVO.ACTIVE)

    async def test_segment_definition_repository_save_inserts_and_gets_dto(
        self,
    ) -> None:
        tenant_id = EntityIdVO.from_value(uuid4())
        segment_id = SegmentIdVO.from_value(uuid4())
        query_gateway = _QueryGatewayStub()
        command_gateway = _CommandGatewayStub(query_gateway)
        repository = SegmentDefinitionRuntimeRepository(
            runtime_object_resolver=_ResolverStub(),
            runtime_command_gateway=command_gateway,
            runtime_query_gateway=query_gateway,
        )

        saved = await repository.save(
            tenant_id=tenant_id,
            segment=SegmentDefinition(
                segment_id=segment_id,
                name="VIP",
                segment_kind=SegmentKindVO.STATIC,
                status=SegmentStatusVO.DRAFT,
                description="Customers",
            ),
        )
        dto = await repository.get(tenant_id=tenant_id, segment_id=segment_id)

        self.assertEqual(saved.segment_id, segment_id)
        self.assertEqual(command_gateway.insert_payloads[0]["name"], "VIP")
        self.assertEqual(dto.description, "Customers")

    async def test_segment_definition_repository_list_uses_page_and_sorting(
        self,
    ) -> None:
        tenant_id = EntityIdVO.from_value(uuid4())
        now = datetime(2026, 5, 28, 12, 0, tzinfo=UTC)
        query_gateway = _QueryGatewayStub()
        query_gateway.rows_by_object["segment_definition"] = [
            {
                "id": uuid4(),
                "created_at": now,
                "updated_at": now,
                "name": "VIP",
                "description": None,
                "segment_kind": "static",
                "status": "draft",
                "archived_at": None,
            }
        ]
        repository = SegmentDefinitionRuntimeRepository(
            runtime_object_resolver=_ResolverStub(),
            runtime_command_gateway=_CommandGatewayStub(query_gateway),
            runtime_query_gateway=query_gateway,
        )

        result = await repository.list(tenant_id=tenant_id, limit=10, offset=5)

        self.assertEqual(len(result), 0)
        self.assertEqual(query_gateway.last_page, PageSpec(limit=10, offset=5))
        self.assertEqual(
            query_gateway.last_sorting,
            (
                SortSpec(field="created_at", direction="asc"),
                SortSpec(field="id", direction="asc"),
            ),
        )

    async def test_segment_version_next_number_locks_before_lookup(self) -> None:
        tenant_id = EntityIdVO.from_value(uuid4())
        segment_id = SegmentIdVO.from_value(uuid4())
        now = datetime(2026, 5, 28, 12, 0, tzinfo=UTC)
        query_gateway = _QueryGatewayStub()
        query_gateway.rows_by_object["segment_version"] = [
            {
                "id": uuid4(),
                "created_at": now,
                "updated_at": now,
                "segment_definition_id": segment_id.uuid,
                "version_number": 4,
                "status": "active",
                "config": {},
                "config_checksum": "abc",
                "activated_at": now,
                "archived_at": None,
            }
        ]
        command_gateway = _CommandGatewayStub(query_gateway)
        repository = SegmentVersionRuntimeRepository(
            runtime_object_resolver=_ResolverStub(),
            runtime_command_gateway=command_gateway,
            runtime_query_gateway=query_gateway,
        )

        next_number = await repository.get_next_version_number(
            tenant_id=tenant_id,
            segment_id=segment_id,
        )

        self.assertEqual(next_number, 5)
        self.assertEqual(query_gateway.events[0].split(":")[0], "lock")
        self.assertEqual(query_gateway.events[1], "list:segment_version")
        self.assertIn(str(tenant_id.uuid), command_gateway.locks[0])
        self.assertIn(str(segment_id.uuid), command_gateway.locks[0])

    async def test_segment_version_save_get_and_list_map_dto(self) -> None:
        tenant_id = EntityIdVO.from_value(uuid4())
        segment_id = SegmentIdVO.from_value(uuid4())
        version_id = SegmentVersionIdVO.from_value(uuid4())
        query_gateway = _QueryGatewayStub()
        repository = SegmentVersionRuntimeRepository(
            runtime_object_resolver=_ResolverStub(),
            runtime_command_gateway=_CommandGatewayStub(query_gateway),
            runtime_query_gateway=query_gateway,
        )

        await repository.save(
            tenant_id=tenant_id,
            version=SegmentVersion(
                segment_version_id=version_id,
                segment_id=segment_id,
                version_number=1,
                status=SegmentVersionStatusVO.DRAFT,
                config={"a": 1},
                config_checksum="abc",
            ),
        )
        dto = await repository.get(
            tenant_id=tenant_id,
            segment_id=segment_id,
            segment_version_id=version_id,
        )
        items = await repository.list(
            tenant_id=tenant_id,
            segment_id=segment_id,
            limit=10,
            offset=0,
        )

        self.assertEqual(dto.config, {"a": 1})
        self.assertEqual(items[0].id, version_id.uuid)
        self.assertEqual(
            query_gateway.last_sorting,
            (
                SortSpec(field="version_number", direction="asc"),
                SortSpec(field="id", direction="asc"),
            ),
        )

    async def test_segment_version_archive_active_versions_updates_by_filter(
        self,
    ) -> None:
        tenant_id = EntityIdVO.from_value(uuid4())
        segment_id = SegmentIdVO.from_value(uuid4())
        now = datetime(2026, 5, 28, 12, 0, tzinfo=UTC)
        query_gateway = _QueryGatewayStub()
        command_gateway = _CommandGatewayStub(query_gateway)
        repository = SegmentVersionRuntimeRepository(
            runtime_object_resolver=_ResolverStub(),
            runtime_command_gateway=command_gateway,
            runtime_query_gateway=query_gateway,
        )

        await repository.archive_active_versions(
            tenant_id=tenant_id,
            segment_id=segment_id,
            now=now,
        )

        filters, patch = command_gateway.update_where_payloads[0]
        self.assertEqual(patch["status"], SegmentVersionStatusVO.ARCHIVED.value)
        self.assertEqual(patch["archived_at"], now)
        self.assertTrue(
            any(
                isinstance(expression, TypedFilterSpec)
                and expression.field.name == "segment_definition_id"
                and expression.value == segment_id.uuid
                for expression in filters
            )
        )

    async def test_contact_lookup_adapter_maps_batch_summaries(self) -> None:
        tenant_id = EntityIdVO.from_value(uuid4())
        contact_id = EntityIdVO.from_value(uuid4())
        query_gateway = _QueryGatewayStub()
        query_gateway.rows_by_object["contact"] = [
            {
                "id": contact_id.uuid,
                "first_name": "Denis",
                "last_name": "Nikon",
                "middle_name": None,
                "status": "active",
            }
        ]
        adapter = RuntimeContactLookupAdapter(
            runtime_object_resolver=_ResolverStub(),
            runtime_query_gateway=query_gateway,
        )

        summaries = await adapter.get_summaries(
            tenant_id=tenant_id,
            contact_ids=[contact_id],
        )

        self.assertEqual(summaries[contact_id.uuid].first_name, "Denis")


__all__ = ["SegmentationRuntimeRepositoryTests"]
