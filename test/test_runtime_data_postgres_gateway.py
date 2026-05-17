from __future__ import annotations

import unittest
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.exc import SQLAlchemyError

from src.modules.runtime_data.application.models import (
    FilterLogic,
    PageSpec,
    SortSpec,
    TypedFilterExpression,
    TypedFilterGroupSpec,
    TypedFilterSpec,
)
from src.modules.runtime_data.application.query.query_plan import RuntimeQueryPlan
from src.modules.runtime_data.application.query.typed_filter_builder import (
    RuntimeTypedFilterBuilder,
)
from src.modules.runtime_data.domain.error import RuntimeDataPersistenceError
from src.modules.runtime_data.infrastructure.persistence.postgres.gateway.command_gateway import (
    PostgresRuntimeCommandGateway,
)
from src.modules.runtime_data.infrastructure.persistence.postgres.gateway.query_gateway import (
    PostgresRuntimeQueryGateway,
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
        self.statements = []
        self.commit_calls = 0
        self.rollback_calls = 0

    async def execute(self, statement, params=None):
        text_value = str(statement)
        self.statements.append(statement)
        self.calls.append((text_value, dict(params or {})))
        if not self._responses:
            raise AssertionError("Unexpected execute call")
        return self._responses.pop(0)

    async def commit(self):
        self.commit_calls += 1

    async def rollback(self):
        self.rollback_calls += 1


class PostgresRuntimePersistenceGatewayTests(unittest.IsolatedAsyncioTestCase):
    def _command_gateway(self, session) -> PostgresRuntimeCommandGateway:
        return PostgresRuntimeCommandGateway(session)  # type: ignore[arg-type]

    def _query_gateway(self, session) -> PostgresRuntimeQueryGateway:
        return PostgresRuntimeQueryGateway(session)  # type: ignore[arg-type]

    def _filter(
        self,
        descriptor: RuntimeObjectDescriptor,
        *,
        field: str,
        op: str,
        value,
    ) -> TypedFilterSpec:
        return RuntimeTypedFilterBuilder().condition(
            descriptor=descriptor,
            field=field,
            op=op,
            value=value,
        )

    def _group(
        self,
        *,
        logic: FilterLogic,
        items: tuple[TypedFilterExpression, ...],
    ) -> TypedFilterGroupSpec:
        return RuntimeTypedFilterBuilder().group(
            logic=logic,
            items=items,
        )

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
                RuntimeFieldDescriptor(
                    name="tags",
                    type_code="multiselect",
                    is_nullable=True,
                    default_value=None,
                    options={
                        "vip": "VIP",
                        "newsletter": "Newsletter",
                        "inactive": "Inactive",
                    },
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
            "tags": ["vip"],
        }
        session = _SessionSpy([_MappingsResult([response_row])])
        gateway = self._command_gateway(session)

        row = await gateway.insert(
            descriptor=self._descriptor(),
            payload={
                "id": str(contact_id),
                "last_name": "Doe",
                "first_name": "Jane",
                "tags": ["vip"],
            },
        )

        self.assertEqual(row["id"], contact_id)
        sql, params = session.calls[0]
        self.assertIn('INSERT INTO "dnk_test"."contacts"', sql)
        self.assertIn(
            'RETURNING "id", "created_at", "updated_at", "last_name", "first_name", "tags"',
            sql,
        )
        self.assertEqual(params["v_1"], "Doe")
        self.assertEqual(params["v_3"], ["vip"])
        self.assertIsInstance(session.statements[0]._bindparams["v_3"].type, JSONB)
        self.assertEqual(session.commit_calls, 0)
        self.assertEqual(session.rollback_calls, 0)

    async def test_update_adds_updated_at_assignment(self) -> None:
        contact_id = uuid4()
        response_row = {
            "id": contact_id,
            "created_at": datetime(2026, 1, 1, 10, 0, 0, tzinfo=UTC),
            "updated_at": datetime(2026, 1, 1, 11, 0, 0, tzinfo=UTC),
            "last_name": "Roe",
            "first_name": "Jane",
            "tags": [],
        }
        session = _SessionSpy([_MappingsResult([response_row])])
        gateway = self._command_gateway(session)

        row = await gateway.update(
            descriptor=self._descriptor(),
            object_id=str(contact_id),
            patch={"last_name": "Roe", "tags": []},
        )

        self.assertIsNotNone(row)
        sql, _params = session.calls[0]
        self.assertIn(
            'SET "last_name" = :p_0, "tags" = :p_1, "updated_at" = CURRENT_TIMESTAMP',
            sql,
        )
        self.assertIn('WHERE "id" = :pk_value', sql)
        self.assertIsInstance(session.statements[0]._bindparams["p_1"].type, JSONB)
        self.assertEqual(session.commit_calls, 0)
        self.assertEqual(session.rollback_calls, 0)

    async def test_update_where_uses_filters_and_returns_rows(self) -> None:
        contact_id = uuid4()
        response_row = {
            "id": contact_id,
            "created_at": datetime(2026, 1, 1, 10, 0, 0, tzinfo=UTC),
            "updated_at": datetime(2026, 1, 1, 11, 0, 0, tzinfo=UTC),
            "last_name": "Roe",
            "first_name": "Jane",
            "tags": [],
        }
        session = _SessionSpy([_MappingsResult([response_row])])
        gateway = self._command_gateway(session)
        descriptor = self._descriptor()

        rows = await gateway.update_where(
            descriptor=descriptor,
            filters=(self._filter(descriptor, field="last_name", op="eq", value=None),),
            patch={"last_name": "Roe"},
        )

        self.assertEqual(rows, [response_row])
        sql, _params = session.calls[0]
        self.assertIn('UPDATE "dnk_test"."contacts"', sql)
        self.assertIn('SET "last_name" = :u_0, "updated_at" = CURRENT_TIMESTAMP', sql)
        self.assertIn('WHERE "last_name" IS NULL', sql)

    async def test_claim_uses_skip_locked_cte_and_limit(self) -> None:
        contact_id = uuid4()
        response_row = {
            "id": contact_id,
            "created_at": datetime(2026, 1, 1, 10, 0, 0, tzinfo=UTC),
            "updated_at": datetime(2026, 1, 1, 11, 0, 0, tzinfo=UTC),
            "last_name": "Doe",
            "first_name": "Jane",
            "tags": [],
        }
        session = _SessionSpy([_MappingsResult([response_row])])
        gateway = self._command_gateway(session)
        descriptor = self._descriptor()

        rows = await gateway.claim(
            descriptor=descriptor,
            filters=(
                self._filter(
                    descriptor,
                    field="first_name",
                    op="in",
                    value=["Jane"],
                ),
            ),
            patch={"last_name": "Claimed"},
            sorting=(SortSpec(field="created_at", direction="asc"),),
            limit=5,
        )

        self.assertEqual(rows, [response_row])
        sql, params = session.calls[0]
        self.assertIn("WITH claimed AS", sql)
        self.assertIn("FOR UPDATE SKIP LOCKED", sql)
        self.assertIn('ORDER BY "created_at" ASC', sql)
        self.assertIn("LIMIT :claim_limit", sql)
        self.assertIn('WHERE "id" IN (SELECT "id" FROM claimed)', sql)
        self.assertEqual(params["claim_limit"], 5)

    async def test_list_supports_filters_sorting_and_pagination(self) -> None:
        contact_id = uuid4()
        response_row = {
            "id": contact_id,
            "created_at": datetime(2026, 1, 1, 10, 0, 0),
            "updated_at": datetime(2026, 1, 1, 11, 0, 0),
            "last_name": "Doe",
            "first_name": "Jane",
            "tags": ["vip"],
        }
        session = _SessionSpy([_MappingsResult([response_row])])
        gateway = self._query_gateway(session)
        descriptor = self._descriptor()

        rows = await gateway.list(
            descriptor=descriptor,
            filters=(
                self._filter(
                    descriptor,
                    field="last_name",
                    op="contains",
                    value="Do",
                ),
            ),
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

    async def test_list_supports_nested_filter_groups(self) -> None:
        contact_id = uuid4()
        response_row = {
            "id": contact_id,
            "created_at": datetime(2026, 1, 1, 10, 0, 0),
            "updated_at": datetime(2026, 1, 1, 11, 0, 0),
            "last_name": "Doe",
            "first_name": "Jane",
            "tags": [],
        }
        session = _SessionSpy([_MappingsResult([response_row])])
        gateway = self._query_gateway(session)
        descriptor = self._descriptor()

        rows = await gateway.list(
            descriptor=descriptor,
            filters=(
                self._group(
                    logic="and",
                    items=(
                        self._filter(
                            descriptor,
                            field="last_name",
                            op="eq",
                            value="Doe",
                        ),
                        self._group(
                            logic="or",
                            items=(
                                self._filter(
                                    descriptor,
                                    field="first_name",
                                    op="contains",
                                    value="Ja",
                                ),
                                self._filter(
                                    descriptor,
                                    field="last_name",
                                    op="contains",
                                    value="Do",
                                ),
                            ),
                        ),
                    ),
                ),
            ),
        )

        self.assertEqual(len(rows), 1)
        sql, params = session.calls[0]
        self.assertIn(
            'WHERE ("last_name" = :f_0 AND '
            "(CAST(\"first_name\" AS text) ILIKE :f_1 ESCAPE '\\' OR "
            "CAST(\"last_name\" AS text) ILIKE :f_2 ESCAPE '\\'))",
            sql,
        )
        self.assertEqual(params["f_0"], "Doe")
        self.assertEqual(params["f_1"], "%Ja%")
        self.assertEqual(params["f_2"], "%Do%")

    async def test_list_supports_text_prefix_and_suffix_filters(self) -> None:
        contact_id = uuid4()
        response_row = {
            "id": contact_id,
            "created_at": datetime(2026, 1, 1, 10, 0, 0),
            "updated_at": datetime(2026, 1, 1, 11, 0, 0),
            "last_name": "Doe",
            "first_name": "Jane",
            "tags": [],
        }
        session = _SessionSpy([_MappingsResult([response_row])])
        gateway = self._query_gateway(session)
        descriptor = self._descriptor()

        rows = await gateway.list(
            descriptor=descriptor,
            filters=(
                self._filter(
                    descriptor,
                    field="last_name",
                    op="starts_with",
                    value="Do_%",
                ),
                self._filter(
                    descriptor,
                    field="first_name",
                    op="ends_with",
                    value="ne%",
                ),
            ),
        )

        self.assertEqual(len(rows), 1)
        sql, params = session.calls[0]
        self.assertIn("CAST(\"last_name\" AS text) ILIKE :f_0 ESCAPE '\\'", sql)
        self.assertIn("CAST(\"first_name\" AS text) ILIKE :f_1 ESCAPE '\\'", sql)
        self.assertEqual(params["f_0"], "Do\\_\\%%")
        self.assertEqual(params["f_1"], "%ne\\%")

    async def test_postgres_compiles_contains_any_for_multiselect(self) -> None:
        contact_id = uuid4()
        response_row = {
            "id": contact_id,
            "created_at": datetime(2026, 1, 1, 10, 0, 0),
            "updated_at": datetime(2026, 1, 1, 11, 0, 0),
            "last_name": "Doe",
            "first_name": "Jane",
            "tags": ["vip"],
        }
        session = _SessionSpy([_MappingsResult([response_row])])
        gateway = self._query_gateway(session)
        descriptor = self._descriptor()

        rows = await gateway.list(
            descriptor=descriptor,
            filters=(
                self._filter(
                    descriptor,
                    field="tags",
                    op="contains_any",
                    value=["vip", "newsletter"],
                ),
            ),
        )

        self.assertEqual(len(rows), 1)
        sql, params = session.calls[0]
        self.assertIn('"tags" ?| array[:f_0_0, :f_0_1]', sql)
        self.assertEqual(params["f_0_0"], "vip")
        self.assertEqual(params["f_0_1"], "newsletter")

    async def test_list_supports_multiselect_filters(self) -> None:
        contact_id = uuid4()
        response_row = {
            "id": contact_id,
            "created_at": datetime(2026, 1, 1, 10, 0, 0),
            "updated_at": datetime(2026, 1, 1, 11, 0, 0),
            "last_name": "Doe",
            "first_name": "Jane",
            "tags": ["vip", "newsletter"],
        }
        session = _SessionSpy([_MappingsResult([response_row])])
        gateway = self._query_gateway(session)
        descriptor = self._descriptor()

        rows = await gateway.list(
            descriptor=descriptor,
            filters=(
                self._filter(
                    descriptor,
                    field="tags",
                    op="contains_all",
                    value=["vip", "newsletter"],
                ),
                self._filter(
                    descriptor,
                    field="tags",
                    op="not_contains_any",
                    value=["inactive"],
                ),
                self._filter(descriptor, field="tags", op="is_empty", value=None),
                self._filter(descriptor, field="tags", op="is_not_empty", value=None),
            ),
        )

        self.assertEqual(len(rows), 1)
        sql, params = session.calls[0]
        self.assertIn('"tags" ?& array[:f_0_0, :f_0_1]', sql)
        self.assertIn('NOT ("tags" ?| array[:f_1_0])', sql)
        self.assertIn('COALESCE(jsonb_array_length("tags"), 0) = 0', sql)
        self.assertIn('COALESCE(jsonb_array_length("tags"), 0) > 0', sql)
        self.assertEqual(params["f_0_0"], "vip")
        self.assertEqual(params["f_0_1"], "newsletter")
        self.assertEqual(params["f_1_0"], "inactive")

    async def test_search_returns_rows_and_total_with_same_filters(self) -> None:
        contact_id = uuid4()
        response_row = {
            "id": contact_id,
            "created_at": datetime(2026, 1, 1, 10, 0, 0),
            "updated_at": datetime(2026, 1, 1, 11, 0, 0),
            "last_name": "Doe",
            "first_name": "Jane",
            "tags": ["vip"],
        }
        session = _SessionSpy(
            [
                _MappingsResult([], scalar_value=42),
                _MappingsResult([response_row]),
            ]
        )
        gateway = self._query_gateway(session)
        descriptor = self._descriptor()

        page = await gateway.search(
            RuntimeQueryPlan(
                descriptor=descriptor,
                filters=(
                    TypedFilterSpec(
                        field=descriptor.fields_by_name["last_name"],
                        op="neq",
                        value="Roe",
                    ),
                    TypedFilterSpec(
                        field=descriptor.fields_by_name["created_at"],
                        op="between",
                        value=(
                            datetime(2026, 1, 1, 0, 0, 0),
                            datetime(2026, 2, 1, 0, 0, 0),
                        ),
                    ),
                    TypedFilterSpec(
                        field=descriptor.fields_by_name["first_name"],
                        op="is_not_null",
                        value=None,
                    ),
                ),
                sorting=(SortSpec(field="created_at", direction="desc"),),
                page=PageSpec(limit=25, offset=10),
            ),
        )

        self.assertEqual(page.total, 42)
        self.assertEqual(len(page.rows), 1)
        count_sql, count_params = session.calls[0]
        page_sql, page_params = session.calls[1]
        self.assertIn("SELECT COUNT(*) AS total", count_sql)
        self.assertIn('"last_name" IS DISTINCT FROM :f_0', count_sql)
        self.assertIn('"created_at" BETWEEN :f_1_start AND :f_1_end', count_sql)
        self.assertIn('"first_name" IS NOT NULL', count_sql)
        self.assertNotIn("LIMIT :page_limit", count_sql)
        self.assertEqual(count_params["f_0"], "Roe")
        self.assertIn('ORDER BY "created_at" DESC', page_sql)
        self.assertIn("LIMIT :page_limit OFFSET :page_offset", page_sql)
        self.assertEqual(page_params["page_limit"], 25)
        self.assertEqual(page_params["page_offset"], 10)

    async def test_sqlalchemy_error_becomes_runtime_persistence_error(self) -> None:
        class FailingSession:
            async def execute(self, statement, params=None):
                raise SQLAlchemyError("boom")

        gateway = self._command_gateway(FailingSession())

        with self.assertRaises(RuntimeDataPersistenceError):
            await gateway.insert(
                descriptor=self._descriptor(),
                payload={
                    "id": str(uuid4()),
                    "first_name": "Jane",
                    "tags": ["vip"],
                },
            )
