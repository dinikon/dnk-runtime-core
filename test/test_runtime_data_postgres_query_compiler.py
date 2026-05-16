from __future__ import annotations

import unittest
from datetime import datetime
from uuid import uuid4

from src.modules.runtime_data import (
    PageSpec,
    PostgresRuntimeGateway,
    RuntimeQueryPlan,
    SortSpec,
    TypedFilterGroupSpec,
    TypedFilterSpec,
)
from src.modules.runtime_data.domain import RuntimeDataPolicyError
from src.modules.runtime_data.infrastructure.persistence.postgres.compiler import (
    CompiledQuery,
    PostgresRuntimeQueryCompiler,
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

    def all(self):
        return list(self._rows)

    def scalar(self):
        return self._scalar_value


class _SessionSpy:
    def __init__(self, responses: list[_MappingsResult]) -> None:
        self._responses = list(responses)
        self.calls: list[tuple[str, dict]] = []

    async def execute(self, statement, params=None):
        self.calls.append((str(statement), dict(params or {})))
        if not self._responses:
            raise AssertionError("Unexpected execute call")
        return self._responses.pop(0)


def _descriptor(*, table_name: str = "contacts") -> RuntimeObjectDescriptor:
    return RuntimeObjectDescriptor(
        schema_name="dnk_test",
        object_name="contact",
        table_name=table_name,
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


def _query_plan(
    *,
    descriptor: RuntimeObjectDescriptor | None = None,
    filters=(),
    sorting=(),
) -> RuntimeQueryPlan:
    return RuntimeQueryPlan(
        descriptor=descriptor or _descriptor(),
        filters=tuple(filters),
        sorting=tuple(sorting),
        page=PageSpec(limit=25, offset=10),
    )


def _typed_filter(
    descriptor: RuntimeObjectDescriptor,
    *,
    field: str,
    op: str,
    value,
) -> TypedFilterSpec:
    field_descriptor = descriptor.field_by_name(field)
    assert field_descriptor is not None
    return TypedFilterSpec(field=field_descriptor, op=op, value=value)


class PostgresRuntimeQueryCompilerTests(unittest.TestCase):
    def test_compiler_compiles_eq_filter(self) -> None:
        descriptor = _descriptor()
        compiled = PostgresRuntimeQueryCompiler().compile_search(
            _query_plan(
                descriptor=descriptor,
                filters=(
                    _typed_filter(
                        descriptor,
                        field="last_name",
                        op="eq",
                        value="Doe",
                    ),
                ),
            )
        )

        self.assertIn('WHERE "last_name" = :f_0', compiled.sql)
        self.assertIn("LIMIT :page_limit OFFSET :page_offset", compiled.sql)
        self.assertEqual(compiled.params["f_0"], "Doe")
        self.assertEqual(compiled.params["page_limit"], 25)
        self.assertEqual(compiled.params["page_offset"], 10)

    def test_compiler_compiles_nested_group(self) -> None:
        descriptor = _descriptor()
        compiled = PostgresRuntimeQueryCompiler().compile_search(
            _query_plan(
                descriptor=descriptor,
                filters=(
                    TypedFilterGroupSpec(
                        logic="and",
                        items=(
                            _typed_filter(
                                descriptor,
                                field="last_name",
                                op="eq",
                                value="Doe",
                            ),
                            TypedFilterGroupSpec(
                                logic="or",
                                items=(
                                    _typed_filter(
                                        descriptor,
                                        field="first_name",
                                        op="contains",
                                        value="Ja",
                                    ),
                                    _typed_filter(
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
        )

        self.assertIn(
            'WHERE ("last_name" = :f_0 AND '
            "(CAST(\"first_name\" AS text) ILIKE :f_1 ESCAPE '\\' OR "
            "CAST(\"last_name\" AS text) ILIKE :f_2 ESCAPE '\\'))",
            compiled.sql,
        )
        self.assertEqual(compiled.params["f_0"], "Doe")
        self.assertEqual(compiled.params["f_1"], "%Ja%")
        self.assertEqual(compiled.params["f_2"], "%Do%")

    def test_compiler_compiles_sort(self) -> None:
        compiled = PostgresRuntimeQueryCompiler().compile_search(
            _query_plan(sorting=(SortSpec(field="created_at", direction="desc"),))
        )

        self.assertIn('ORDER BY "created_at" DESC', compiled.sql)

    def test_compiler_uses_typed_value_without_recoercion(self) -> None:
        descriptor = _descriptor()
        sentinel_value = object()
        compiled = PostgresRuntimeQueryCompiler().compile_search(
            _query_plan(
                descriptor=descriptor,
                filters=(
                    _typed_filter(
                        descriptor,
                        field="created_at",
                        op="gte",
                        value=sentinel_value,
                    ),
                ),
            )
        )

        self.assertIs(compiled.params["f_0"], sentinel_value)

    def test_compiler_rejects_invalid_identifier(self) -> None:
        with self.assertRaises(RuntimeDataPolicyError):
            PostgresRuntimeQueryCompiler().compile_search(
                _query_plan(descriptor=_descriptor(table_name="bad-name"))
            )


class PostgresRuntimeGatewayCompilerFlowTests(unittest.IsolatedAsyncioTestCase):
    async def test_gateway_uses_compiler_for_search(self) -> None:
        contact_id = uuid4()
        query_plan = _query_plan()

        class QueryCompilerSpy:
            count_plan = None
            search_plan = None

            def compile_count(self, plan):
                self.count_plan = plan
                return CompiledQuery(
                    sql="SELECT 1 AS total",
                    params={"count_param": "count"},
                )

            def compile_search(self, plan):
                self.search_plan = plan
                return CompiledQuery(
                    sql="SELECT * FROM compiled_search",
                    params={"page_param": "page"},
                )

        row = {
            "id": contact_id,
            "created_at": datetime(2026, 1, 1, 10, 0, 0),
            "last_name": "Doe",
            "first_name": "Jane",
        }
        session = _SessionSpy(
            [
                _MappingsResult([], scalar_value=9),
                _MappingsResult([row]),
            ]
        )
        compiler = QueryCompilerSpy()
        gateway = PostgresRuntimeGateway(
            session,  # type: ignore[arg-type]
            query_compiler=compiler,  # type: ignore[arg-type]
        )

        page = await gateway.search(query_plan)

        self.assertIs(compiler.count_plan, query_plan)
        self.assertIs(compiler.search_plan, query_plan)
        self.assertEqual(
            session.calls[0], ("SELECT 1 AS total", {"count_param": "count"})
        )
        self.assertEqual(
            session.calls[1],
            ("SELECT * FROM compiled_search", {"page_param": "page"}),
        )
        self.assertEqual(page.total, 9)
        self.assertEqual(page.rows[0]["id"], contact_id)


__all__ = [
    "PostgresRuntimeGatewayCompilerFlowTests",
    "PostgresRuntimeQueryCompilerTests",
]
