from __future__ import annotations

import unittest
from datetime import datetime
from uuid import uuid4

from src.modules.runtime_data import (
    FilterSpec,
    PageSpec,
    PostgresRuntimeGateway,
    SortSpec,
)
from src.modules.schema_registry.runtime import (
    RuntimeFieldDescriptor,
    RuntimeObjectDescriptor,
)


class _MappingsResult:
    def __init__(self, rows: list[dict], scalar_value=None) -> None:
        self._rows = rows
        self._scalar_value = scalar_value

    def mappings(self):
        return self

    def first(self):
        if not self._rows:
            return None
        return self._rows[0]

    def all(self):
        return list(self._rows)

    def scalar(self):
        if self._scalar_value is not None:
            return self._scalar_value
        if not self._rows:
            return None
        first_row = self._rows[0]
        if not first_row:
            return None
        return next(iter(first_row.values()))


class _SessionSpy:
    def __init__(self, responses: list[_MappingsResult]) -> None:
        self._responses = list(responses)
        self.calls: list[tuple[str, dict]] = []
        self.commit_calls = 0
        self.rollback_calls = 0

    async def execute(self, statement, params=None):
        text_value = str(statement)
        self.calls.append((text_value, dict(params or {})))
        if not self._responses:
            raise AssertionError("Unexpected execute call")
        return self._responses.pop(0)

    async def commit(self):
        self.commit_calls += 1

    async def rollback(self):
        self.rollback_calls += 1


class PostgresRuntimeGatewayTests(unittest.IsolatedAsyncioTestCase):
    def _descriptor(self) -> RuntimeObjectDescriptor:
        return RuntimeObjectDescriptor(
            schema_name="dnk_test",
            object_name="contact",
            table_name="contacts",
            pk="id",
            title_field="id",
            fields=(
                RuntimeFieldDescriptor(
                    name="id",
                    type_code="uuid",
                    is_nullable=False,
                    default_value="gen_random_uuid()",
                    options={},
                    settings={},
                ),
                RuntimeFieldDescriptor(
                    name="created_at",
                    type_code="datetime",
                    is_nullable=False,
                    default_value="CURRENT_TIMESTAMP",
                    options={},
                    settings={},
                ),
                RuntimeFieldDescriptor(
                    name="updated_at",
                    type_code="datetime",
                    is_nullable=False,
                    default_value="CURRENT_TIMESTAMP",
                    options={},
                    settings={},
                ),
                RuntimeFieldDescriptor(
                    name="last_name",
                    type_code="text",
                    is_nullable=True,
                    default_value=None,
                    options={},
                    settings={},
                ),
                RuntimeFieldDescriptor(
                    name="first_name",
                    type_code="text",
                    is_nullable=False,
                    default_value=None,
                    options={},
                    settings={},
                ),
            ),
            relations=(),
        )

    async def test_insert_uses_session_bound_execute_without_commit(self) -> None:
        contact_id = uuid4()
        response_row = {
            "id": contact_id,
            "created_at": datetime(2026, 1, 1, 10, 0, 0),
            "updated_at": datetime(2026, 1, 1, 10, 0, 0),
            "last_name": "Doe",
            "first_name": "Jane",
        }
        session = _SessionSpy([_MappingsResult([response_row])])
        gateway = PostgresRuntimeGateway(session)  # type: ignore[arg-type]

        row = await gateway.insert(
            descriptor=self._descriptor(),
            payload={
                "id": str(contact_id),
                "last_name": "Doe",
                "first_name": "Jane",
            },
        )

        self.assertEqual(row["id"], contact_id)
        sql, params = session.calls[0]
        self.assertIn('INSERT INTO "dnk_test"."contacts"', sql)
        self.assertIn(
            'RETURNING "id", "created_at", "updated_at", "last_name", "first_name"', sql
        )
        self.assertEqual(params["v_1"], "Doe")
        self.assertEqual(session.commit_calls, 0)
        self.assertEqual(session.rollback_calls, 0)

    async def test_update_adds_updated_at_assignment(self) -> None:
        contact_id = uuid4()
        response_row = {
            "id": contact_id,
            "created_at": datetime(2026, 1, 1, 10, 0, 0),
            "updated_at": datetime(2026, 1, 1, 11, 0, 0),
            "last_name": "Roe",
            "first_name": "Jane",
        }
        session = _SessionSpy([_MappingsResult([response_row])])
        gateway = PostgresRuntimeGateway(session)  # type: ignore[arg-type]

        row = await gateway.update(
            descriptor=self._descriptor(),
            object_id=str(contact_id),
            patch={"last_name": "Roe"},
        )

        self.assertIsNotNone(row)
        sql, _params = session.calls[0]
        self.assertIn('SET "last_name" = :p_0, "updated_at" = CURRENT_TIMESTAMP', sql)
        self.assertIn('WHERE "id" = :pk_value', sql)
        self.assertEqual(session.commit_calls, 0)
        self.assertEqual(session.rollback_calls, 0)

    async def test_list_supports_filters_sorting_and_pagination(self) -> None:
        contact_id = uuid4()
        response_row = {
            "id": contact_id,
            "created_at": datetime(2026, 1, 1, 10, 0, 0),
            "updated_at": datetime(2026, 1, 1, 11, 0, 0),
            "last_name": "Doe",
            "first_name": "Jane",
        }
        session = _SessionSpy([_MappingsResult([response_row])])
        gateway = PostgresRuntimeGateway(session)  # type: ignore[arg-type]

        rows = await gateway.list(
            descriptor=self._descriptor(),
            filters=(FilterSpec(field="last_name", op="contains", value="Do"),),
            sorting=(SortSpec(field="created_at", direction="desc"),),
            page=PageSpec(limit=25, offset=10),
        )

        self.assertEqual(len(rows), 1)
        sql, params = session.calls[0]
        self.assertIn("ILIKE", sql)
        self.assertIn('ORDER BY "created_at" DESC', sql)
        self.assertIn("LIMIT :page_limit OFFSET :page_offset", sql)
        self.assertEqual(params["page_limit"], 25)
        self.assertEqual(params["page_offset"], 10)
