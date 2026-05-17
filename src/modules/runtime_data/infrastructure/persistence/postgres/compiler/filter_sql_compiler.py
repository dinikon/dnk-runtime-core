from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from src.modules.runtime_data.application.models import (
    TypedFilterExpression,
    TypedFilterGroupSpec,
    TypedFilterSpec,
)
from src.modules.runtime_data.domain.error import RuntimeDataFilterError
from src.modules.runtime_data.infrastructure.persistence.postgres.compiler.compiled_query import (
    CompiledQuery,
)
from src.modules.runtime_data.infrastructure.persistence.postgres.compiler.identifier import (
    quote_identifier,
)
from src.modules.schema_registry.runtime import RuntimeFieldDescriptor


def escape_like(value: str) -> str:
    """Escape PostgreSQL LIKE wildcards for literal user search text."""
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


class PostgresFilterSqlCompiler:
    """Compiles validated runtime filter specs to PostgreSQL WHERE SQL."""

    def compile_where(
        self,
        *,
        filters: Sequence[TypedFilterExpression],
    ) -> CompiledQuery:
        params: dict[str, Any] = {}
        bind_fields: dict[str, RuntimeFieldDescriptor] = {}
        where_parts: list[str] = []
        position = 0
        for filter_spec in filters:
            (
                where_sql,
                where_params,
                where_bind_fields,
                position,
            ) = self._compile_expression(
                filter_spec=filter_spec,
                position=position,
            )
            where_parts.append(where_sql)
            params.update(where_params)
            bind_fields.update(where_bind_fields)
        where_sql = f"WHERE {' AND '.join(where_parts)}" if where_parts else ""
        return CompiledQuery(sql=where_sql, params=params, bind_fields=bind_fields)

    def _compile_expression(
        self,
        *,
        filter_spec: TypedFilterExpression,
        position: int,
    ) -> tuple[str, dict[str, Any], dict[str, RuntimeFieldDescriptor], int]:
        if isinstance(filter_spec, TypedFilterSpec):
            where_sql, where_params, where_bind_fields = self._compile_clause(
                filter_spec=filter_spec,
                position=position,
            )
            return where_sql, where_params, where_bind_fields, position + 1

        if isinstance(filter_spec, TypedFilterGroupSpec):
            logic = str(filter_spec.logic).strip().lower()
            if logic not in {"and", "or"}:
                raise RuntimeDataFilterError(
                    code="UNSUPPORTED_FILTER_GROUP_LOGIC",
                    message=f"Unsupported filter group logic '{filter_spec.logic}'.",
                    details={
                        "logic": filter_spec.logic,
                    },
                )
            if not filter_spec.items:
                raise RuntimeDataFilterError(
                    code="INVALID_FILTER_GROUP",
                    message=f"Filter group '{logic}' requires at least one item.",
                    details={
                        "logic": logic,
                    },
                )

            parts: list[str] = []
            params: dict[str, Any] = {}
            bind_fields: dict[str, RuntimeFieldDescriptor] = {}
            next_position = position
            for item in filter_spec.items:
                (
                    item_sql,
                    item_params,
                    item_bind_fields,
                    next_position,
                ) = self._compile_expression(
                    filter_spec=item,
                    position=next_position,
                )
                parts.append(item_sql)
                params.update(item_params)
                bind_fields.update(item_bind_fields)

            joiner = f" {logic.upper()} "
            return (
                f"({joiner.join(parts)})",
                params,
                bind_fields,
                next_position,
            )

        raise RuntimeDataFilterError(
            code="UNSUPPORTED_FILTER_EXPRESSION",
            message=f"Unsupported filter expression '{type(filter_spec).__name__}'.",
            details={
                "expression_type": type(filter_spec).__name__,
            },
        )

    def _compile_clause(
        self,
        *,
        filter_spec: TypedFilterSpec,
        position: int,
    ) -> tuple[str, dict[str, Any], dict[str, RuntimeFieldDescriptor]]:
        field = filter_spec.field
        op = filter_spec.op
        field_sql = quote_identifier(field.name)
        value = filter_spec.value

        if op == "eq":
            if value is None:
                return (f"{field_sql} IS NULL", {}, {})
            param_name = f"f_{position}"
            return (
                f"{field_sql} = :{param_name}",
                {param_name: value},
                {param_name: field},
            )

        if op == "neq":
            if value is None:
                return (f"{field_sql} IS NOT NULL", {}, {})
            param_name = f"f_{position}"
            return (
                f"{field_sql} IS DISTINCT FROM :{param_name}",
                {param_name: value},
                {param_name: field},
            )

        if op == "in":
            if not isinstance(value, Sequence) or isinstance(
                value,
                (str, bytes),
            ):
                raise RuntimeDataFilterError(
                    code="INVALID_FILTER_VALUE_TYPE",
                    message=(
                        f"Filter '{field.name}' with operator 'in' "
                        "requires a non-string sequence."
                    ),
                    details={
                        "field": field.name,
                        "operator": op,
                    },
                )
            items = list(value)
            if not items:
                raise RuntimeDataFilterError(
                    code="INVALID_FILTER_VALUE_TYPE",
                    message=(
                        f"Filter '{field.name}' with operator 'in' "
                        "requires at least one value."
                    ),
                    details={
                        "field": field.name,
                        "operator": op,
                    },
                )
            params: dict[str, Any] = {}
            bind_fields: dict[str, RuntimeFieldDescriptor] = {}
            placeholders: list[str] = []
            for item_index, item in enumerate(items):
                param_name = f"f_{position}_{item_index}"
                placeholders.append(f":{param_name}")
                params[param_name] = item
                bind_fields[param_name] = field
            return (f"{field_sql} IN ({', '.join(placeholders)})", params, bind_fields)

        if op == "contains":
            param_name = f"f_{position}"
            return (
                f"CAST({field_sql} AS text) ILIKE :{param_name} ESCAPE '\\'",
                {param_name: f"%{escape_like(value)}%"},
                {},
            )

        if op in {"starts_with", "ends_with"}:
            escaped_value = escape_like(value)
            pattern = (
                f"{escaped_value}%" if op == "starts_with" else f"%{escaped_value}"
            )
            param_name = f"f_{position}"
            return (
                f"CAST({field_sql} AS text) ILIKE :{param_name} ESCAPE '\\'",
                {param_name: pattern},
                {},
            )

        if op in {"contains_any", "contains_all", "not_contains_any"}:
            if not isinstance(value, Sequence) or isinstance(
                value,
                (str, bytes),
            ):
                raise RuntimeDataFilterError(
                    code="INVALID_FILTER_VALUE_TYPE",
                    message=(
                        f"Filter '{field.name}' with operator '{op}' "
                        "requires a non-string sequence."
                    ),
                    details={
                        "field": field.name,
                        "operator": op,
                    },
                )
            items = list(value)
            if not items:
                raise RuntimeDataFilterError(
                    code="INVALID_FILTER_VALUE_TYPE",
                    message=(
                        f"Filter '{field.name}' with operator '{op}' "
                        "requires at least one value."
                    ),
                    details={
                        "field": field.name,
                        "operator": op,
                    },
                )
            params: dict[str, Any] = {}
            placeholders: list[str] = []
            for item_index, item in enumerate(items):
                param_name = f"f_{position}_{item_index}"
                placeholders.append(f":{param_name}")
                params[param_name] = item
            array_sql = f"array[{', '.join(placeholders)}]"
            if op == "contains_all":
                return (f"{field_sql} ?& {array_sql}", params, {})
            if op == "not_contains_any":
                return (f"NOT ({field_sql} ?| {array_sql})", params, {})
            return (f"{field_sql} ?| {array_sql}", params, {})

        if op in {"gt", "gte", "lt", "lte"}:
            param_name = f"f_{position}"
            comparison = {
                "gt": ">",
                "gte": ">=",
                "lt": "<",
                "lte": "<=",
            }[op]
            return (
                f"{field_sql} {comparison} :{param_name}",
                {param_name: value},
                {param_name: field},
            )

        if op == "between":
            start, end = value
            start_param = f"f_{position}_start"
            end_param = f"f_{position}_end"
            return (
                f"{field_sql} BETWEEN :{start_param} AND :{end_param}",
                {
                    start_param: start,
                    end_param: end,
                },
                {
                    start_param: field,
                    end_param: field,
                },
            )

        if op == "is_empty":
            return (f"COALESCE(jsonb_array_length({field_sql}), 0) = 0", {}, {})

        if op == "is_not_empty":
            return (f"COALESCE(jsonb_array_length({field_sql}), 0) > 0", {}, {})

        if op == "is_null":
            return (f"{field_sql} IS NULL", {}, {})

        if op == "is_not_null":
            return (f"{field_sql} IS NOT NULL", {}, {})

        raise RuntimeDataFilterError(
            code="UNSUPPORTED_FILTER_OPERATOR",
            message=f"Unsupported filter operator '{op}'.",
            details={
                "field": field.name,
                "operator": op,
            },
        )


__all__ = ["PostgresFilterSqlCompiler", "escape_like"]
