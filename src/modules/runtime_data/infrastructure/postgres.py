from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any

from sqlalchemy import bindparam, text
from sqlalchemy.dialects import postgresql
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import TextClause

from src.modules.runtime_data.application.models import (
    FetchPlan,
    FilterExpression,
    FilterGroupSpec,
    FilterSpec,
    PageSpec,
    RuntimeRowsPage,
    SortSpec,
)
from src.modules.runtime_data.application.ports import (
    RuntimeCommandGateway,
    RuntimeQueryGateway,
    RuntimeRelationCommandGateway,
    RuntimeRelationLoader,
)
from src.modules.runtime_data.application.type_policy import RuntimeFieldTypePolicy
from src.modules.runtime_data.domain import (
    RuntimeDataFilterError,
    RuntimeDataPersistenceError,
    RuntimeDataPolicyError,
    RuntimeDataValidationError,
)
from src.modules.schema_registry.runtime import (
    RuntimeFieldDescriptor,
    RuntimeObjectDescriptor,
    RuntimeRelationDescriptor,
)

_IDENTIFIER_RE = re.compile(r"^[a-z][a-z0-9_]*$")


class PostgresRuntimeGateway(RuntimeCommandGateway, RuntimeQueryGateway):
    """PostgreSQL gateway для CRUD-операций runtime-данных по descriptor."""

    def __init__(
        self,
        session: AsyncSession,
        type_policy: RuntimeFieldTypePolicy | None = None,
        relation_loader: RuntimeRelationLoader | None = None,
    ) -> None:
        """Инициализирует gateway async-сессией и политикой runtime-типов."""
        self._session = session
        self._type_policy = type_policy or RuntimeFieldTypePolicy()
        self._relation_loader = relation_loader or PostgresRuntimeRelationLoader(
            session=session,
        )

    async def insert(
        self,
        descriptor: RuntimeObjectDescriptor,
        payload: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        """Вставляет runtime-запись, приводя payload к типам descriptor."""
        self._ensure_descriptor(descriptor)
        coerced_payload = self._type_policy.coerce_insert_payload(
            descriptor=descriptor,
            payload=payload,
        )
        table_ref = self._qualified_table(descriptor)
        selected_columns = self._selectable_columns(
            descriptor=descriptor, fetch_plan=None
        )

        if coerced_payload:
            columns: list[str] = []
            values: list[str] = []
            params: dict[str, Any] = {}
            bind_fields: dict[str, RuntimeFieldDescriptor] = {}
            for index, (field_name, value) in enumerate(coerced_payload.items()):
                field = descriptor.fields_by_name[field_name]
                columns.append(self._qi(field_name))
                param_name = f"v_{index}"
                values.append(f":{param_name}")
                params[param_name] = value
                bind_fields[param_name] = field
            sql = (
                f"INSERT INTO {table_ref} ({', '.join(columns)}) "
                f"VALUES ({', '.join(values)}) "
                f"RETURNING {', '.join(selected_columns)}"
            )
            result = await self._execute(sql, params, bind_fields=bind_fields)
        else:
            sql = f"INSERT INTO {table_ref} DEFAULT VALUES RETURNING {', '.join(selected_columns)}"
            result = await self._execute(sql)

        row = result.mappings().first()
        if row is None:
            raise RuntimeDataPolicyError("Insert operation did not return a row.")
        return self._type_policy.normalize_row(descriptor=descriptor, row=row)

    async def update(
        self,
        *,
        descriptor: RuntimeObjectDescriptor,
        object_id: Any,
        patch: Mapping[str, Any],
    ) -> Mapping[str, Any] | None:
        """Обновляет runtime-запись по primary key и возвращает свежую строку."""
        self._ensure_descriptor(descriptor)
        coerced_patch = self._type_policy.coerce_patch_payload(
            descriptor=descriptor,
            patch=patch,
        )

        pk_field = self._required_field(descriptor, descriptor.pk)
        pk_value = self._type_policy.coerce_value_for_field(
            field=pk_field,
            raw_value=object_id,
        )

        set_clauses: list[str] = []
        params: dict[str, Any] = {"pk_value": pk_value}
        bind_fields: dict[str, RuntimeFieldDescriptor] = {"pk_value": pk_field}

        for index, (field_name, value) in enumerate(coerced_patch.items()):
            field = descriptor.fields_by_name[field_name]
            param_name = f"p_{index}"
            set_clauses.append(f"{self._qi(field_name)} = :{param_name}")
            params[param_name] = value
            bind_fields[param_name] = field

        if descriptor.field_by_name("updated_at") is not None:
            set_clauses.append(f'{self._qi("updated_at")} = CURRENT_TIMESTAMP')

        if not set_clauses:
            return await self.get_by_id(
                descriptor=descriptor,
                object_id=pk_value,
            )

        table_ref = self._qualified_table(descriptor)
        selected_columns = self._selectable_columns(
            descriptor=descriptor, fetch_plan=None
        )
        sql = (
            f"UPDATE {table_ref} "
            f"SET {', '.join(set_clauses)} "
            f"WHERE {self._qi(descriptor.pk)} = :pk_value "
            f"RETURNING {', '.join(selected_columns)}"
        )

        result = await self._execute(sql, params, bind_fields=bind_fields)
        row = result.mappings().first()
        if row is None:
            return None
        return self._type_policy.normalize_row(descriptor=descriptor, row=row)

    async def delete(
        self,
        *,
        descriptor: RuntimeObjectDescriptor,
        object_id: Any,
    ) -> bool:
        """Удаляет runtime-запись по primary key и сообщает, была ли она найдена."""
        self._ensure_descriptor(descriptor)
        pk_field = self._required_field(descriptor, descriptor.pk)
        pk_value = self._type_policy.coerce_value_for_field(
            field=pk_field,
            raw_value=object_id,
        )
        sql = (
            f"DELETE FROM {self._qualified_table(descriptor)} "
            f"WHERE {self._qi(descriptor.pk)} = :pk_value "
            f"RETURNING {self._qi(descriptor.pk)}"
        )
        result = await self._execute(
            sql, {"pk_value": pk_value}, bind_fields={"pk_value": pk_field}
        )
        return result.scalar() is not None

    async def update_where(
        self,
        *,
        descriptor: RuntimeObjectDescriptor,
        filters: Sequence[FilterExpression],
        patch: Mapping[str, Any],
    ) -> list[Mapping[str, Any]]:
        """Обновляет runtime-строки по фильтрам и возвращает свежие значения."""
        self._ensure_descriptor(descriptor)
        coerced_patch = self._type_policy.coerce_patch_payload(
            descriptor=descriptor,
            patch=patch,
        )
        set_clauses, params, bind_fields = self._build_set_clauses(
            descriptor=descriptor,
            patch=coerced_patch,
        )
        if not set_clauses:
            return []

        where_sql, where_params, where_bind_fields = self._build_where_clause(
            descriptor=descriptor,
            filters=filters,
        )
        params.update(where_params)
        bind_fields.update(where_bind_fields)

        sql = (
            f"UPDATE {self._qualified_table(descriptor)} "
            f"SET {', '.join(set_clauses)} "
            f"{where_sql} "
            f"RETURNING {', '.join(self._selectable_columns(descriptor=descriptor, fetch_plan=None))}"
        )
        result = await self._execute(sql, params, bind_fields=bind_fields)
        return [
            self._type_policy.normalize_row(descriptor=descriptor, row=row)
            for row in result.mappings().all()
        ]

    async def claim(
        self,
        *,
        descriptor: RuntimeObjectDescriptor,
        filters: Sequence[FilterExpression],
        patch: Mapping[str, Any],
        sorting: Sequence[SortSpec] = (),
        limit: int = 1,
    ) -> list[Mapping[str, Any]]:
        """Claims rows with SKIP LOCKED, applies patch, and returns claimed rows."""
        self._ensure_descriptor(descriptor)
        if limit < 1:
            raise RuntimeDataValidationError("Claim limit must be >= 1.")
        coerced_patch = self._type_policy.coerce_patch_payload(
            descriptor=descriptor,
            patch=patch,
        )
        set_clauses, params, bind_fields = self._build_set_clauses(
            descriptor=descriptor,
            patch=coerced_patch,
        )
        if not set_clauses:
            return []

        where_sql, where_params, where_bind_fields = self._build_where_clause(
            descriptor=descriptor,
            filters=filters,
        )
        params.update(where_params)
        bind_fields.update(where_bind_fields)
        params["claim_limit"] = limit
        order_sql = self._build_sort_clause(descriptor=descriptor, sorting=sorting)
        table_ref = self._qualified_table(descriptor)
        pk_sql = self._qi(descriptor.pk)
        columns = self._selectable_columns(descriptor=descriptor, fetch_plan=None)
        sql = (
            "WITH claimed AS ("
            f"SELECT {pk_sql} FROM {table_ref} "
            f"{where_sql} "
            f"{order_sql} "
            "LIMIT :claim_limit "
            "FOR UPDATE SKIP LOCKED"
            ") "
            f"UPDATE {table_ref} "
            f"SET {', '.join(set_clauses)} "
            f"WHERE {pk_sql} IN (SELECT {pk_sql} FROM claimed) "
            f"RETURNING {', '.join(columns)}"
        )
        result = await self._execute(sql, params, bind_fields=bind_fields)
        return [
            self._type_policy.normalize_row(descriptor=descriptor, row=row)
            for row in result.mappings().all()
        ]

    async def get_by_id(
        self,
        *,
        descriptor: RuntimeObjectDescriptor,
        object_id: Any,
        fetch_plan: FetchPlan | None = None,
    ) -> Mapping[str, Any] | None:
        """Возвращает runtime-запись по primary key с учетом projection."""
        self._ensure_descriptor(descriptor)
        pk_field = self._required_field(descriptor, descriptor.pk)
        pk_value = self._type_policy.coerce_value_for_field(
            field=pk_field,
            raw_value=object_id,
        )

        columns = self._selectable_columns(descriptor=descriptor, fetch_plan=fetch_plan)
        sql = (
            f"SELECT {', '.join(columns)} "
            f"FROM {self._qualified_table(descriptor)} "
            f"WHERE {self._qi(descriptor.pk)} = :pk_value "
            "LIMIT 1"
        )
        result = await self._execute(
            sql, {"pk_value": pk_value}, bind_fields={"pk_value": pk_field}
        )
        row = result.mappings().first()
        if row is None:
            return None
        normalized = self._type_policy.normalize_row(descriptor=descriptor, row=row)
        rows = await self._load_relations_if_needed(
            descriptor=descriptor,
            rows=[normalized],
            fetch_plan=fetch_plan,
        )
        return rows[0] if rows else None

    async def list(
        self,
        *,
        descriptor: RuntimeObjectDescriptor,
        filters: Sequence[FilterExpression] = (),
        sorting: Sequence[SortSpec] = (),
        page: PageSpec | None = None,
        fetch_plan: FetchPlan | None = None,
    ) -> list[Mapping[str, Any]]:
        """Возвращает список runtime-записей с filters, sorting, pagination и projection."""
        self._ensure_descriptor(descriptor)
        columns = self._selectable_columns(descriptor=descriptor, fetch_plan=fetch_plan)

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
            ) = self._build_filter_expression(
                descriptor=descriptor,
                filter_spec=filter_spec,
                position=position,
            )
            where_parts.append(where_sql)
            params.update(where_params)
            bind_fields.update(where_bind_fields)

        order_sql = self._build_sort_clause(descriptor=descriptor, sorting=sorting)

        sql_parts = [
            f"SELECT {', '.join(columns)}",
            f"FROM {self._qualified_table(descriptor)}",
        ]
        if where_parts:
            sql_parts.append(f"WHERE {' AND '.join(where_parts)}")
        if order_sql:
            sql_parts.append(order_sql)
        if page is not None:
            if page.limit < 1:
                raise RuntimeDataValidationError("Page limit must be >= 1.")
            if page.offset < 0:
                raise RuntimeDataValidationError("Page offset must be >= 0.")
            sql_parts.append("LIMIT :page_limit OFFSET :page_offset")
            params["page_limit"] = page.limit
            params["page_offset"] = page.offset

        result = await self._execute(
            " ".join(sql_parts),
            params,
            bind_fields=bind_fields,
        )
        rows = result.mappings().all()
        normalized_rows = [
            self._type_policy.normalize_row(descriptor=descriptor, row=row)
            for row in rows
        ]
        return await self._load_relations_if_needed(
            descriptor=descriptor,
            rows=normalized_rows,
            fetch_plan=fetch_plan,
        )

    async def search(
        self,
        *,
        descriptor: RuntimeObjectDescriptor,
        filters: Sequence[FilterExpression] = (),
        sorting: Sequence[SortSpec] = (),
        page: PageSpec,
        fetch_plan: FetchPlan | None = None,
    ) -> RuntimeRowsPage:
        """Возвращает runtime-страницу с total count по тем же фильтрам."""
        self._ensure_descriptor(descriptor)
        if page.limit < 1:
            raise RuntimeDataValidationError("Page limit must be >= 1.")
        if page.offset < 0:
            raise RuntimeDataValidationError("Page offset must be >= 0.")

        columns = self._selectable_columns(descriptor=descriptor, fetch_plan=fetch_plan)
        where_parts: list[str] = []
        params: dict[str, Any] = {}
        bind_fields: dict[str, RuntimeFieldDescriptor] = {}
        position = 0
        for filter_spec in filters:
            (
                where_sql,
                where_params,
                where_bind_fields,
                position,
            ) = self._build_filter_expression(
                descriptor=descriptor,
                filter_spec=filter_spec,
                position=position,
            )
            where_parts.append(where_sql)
            params.update(where_params)
            bind_fields.update(where_bind_fields)

        where_sql = f"WHERE {' AND '.join(where_parts)}" if where_parts else ""
        table_ref = self._qualified_table(descriptor)
        count_sql = f"SELECT COUNT(*) AS total FROM {table_ref} {where_sql}"
        count_result = await self._execute(
            count_sql,
            dict(params),
            bind_fields=bind_fields,
        )
        total = int(count_result.scalar() or 0)

        page_params = dict(params)
        page_params["page_limit"] = page.limit
        page_params["page_offset"] = page.offset
        order_sql = self._build_sort_clause(descriptor=descriptor, sorting=sorting)
        sql_parts = [
            f"SELECT {', '.join(columns)}",
            f"FROM {table_ref}",
        ]
        if where_sql:
            sql_parts.append(where_sql)
        if order_sql:
            sql_parts.append(order_sql)
        sql_parts.append("LIMIT :page_limit OFFSET :page_offset")
        result = await self._execute(
            " ".join(sql_parts),
            page_params,
            bind_fields=bind_fields,
        )
        rows = result.mappings().all()
        normalized_rows = [
            self._type_policy.normalize_row(descriptor=descriptor, row=row)
            for row in rows
        ]
        loaded_rows = await self._load_relations_if_needed(
            descriptor=descriptor,
            rows=normalized_rows,
            fetch_plan=fetch_plan,
        )
        return RuntimeRowsPage(rows=tuple(loaded_rows), total=total)

    async def _load_relations_if_needed(
        self,
        *,
        descriptor: RuntimeObjectDescriptor,
        rows: Sequence[Mapping[str, Any]],
        fetch_plan: FetchPlan | None,
    ) -> list[Mapping[str, Any]]:
        """Дозагружает relation data, если fetch_plan содержит relations."""
        if fetch_plan is None or not fetch_plan.relations or not rows:
            return [dict(row) for row in rows]
        return await self._relation_loader.load(
            descriptor=descriptor,
            rows=rows,
            fetch_plan=fetch_plan,
        )

    def _build_filter_expression(
        self,
        *,
        descriptor: RuntimeObjectDescriptor,
        filter_spec: FilterExpression,
        position: int,
    ) -> tuple[str, dict[str, Any], dict[str, RuntimeFieldDescriptor], int]:
        """Строит SQL-фрагмент WHERE для одиночного фильтра или AND/OR группы."""
        if isinstance(filter_spec, FilterSpec):
            where_sql, where_params, where_bind_fields = self._build_filter_clause(
                descriptor=descriptor,
                filter_spec=filter_spec,
                position=position,
            )
            return where_sql, where_params, where_bind_fields, position + 1

        if isinstance(filter_spec, FilterGroupSpec):
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
                ) = self._build_filter_expression(
                    descriptor=descriptor,
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

    def _build_where_clause(
        self,
        *,
        descriptor: RuntimeObjectDescriptor,
        filters: Sequence[FilterExpression],
    ) -> tuple[str, dict[str, Any], dict[str, RuntimeFieldDescriptor]]:
        """Строит WHERE для update/claim операций."""
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
            ) = self._build_filter_expression(
                descriptor=descriptor,
                filter_spec=filter_spec,
                position=position,
            )
            where_parts.append(where_sql)
            params.update(where_params)
            bind_fields.update(where_bind_fields)
        where_sql = f"WHERE {' AND '.join(where_parts)}" if where_parts else ""
        return where_sql, params, bind_fields

    def _build_set_clauses(
        self,
        *,
        descriptor: RuntimeObjectDescriptor,
        patch: Mapping[str, Any],
    ) -> tuple[list[str], dict[str, Any], dict[str, RuntimeFieldDescriptor]]:
        """Строит SET clauses для update/claim операций."""
        set_clauses: list[str] = []
        params: dict[str, Any] = {}
        bind_fields: dict[str, RuntimeFieldDescriptor] = {}
        for index, (field_name, value) in enumerate(patch.items()):
            field = descriptor.fields_by_name[field_name]
            param_name = f"u_{index}"
            set_clauses.append(f"{self._qi(field_name)} = :{param_name}")
            params[param_name] = value
            bind_fields[param_name] = field
        if descriptor.field_by_name("updated_at") is not None:
            set_clauses.append(f'{self._qi("updated_at")} = CURRENT_TIMESTAMP')
        return set_clauses, params, bind_fields

    def _build_filter_clause(
        self,
        *,
        descriptor: RuntimeObjectDescriptor,
        filter_spec: FilterSpec,
        position: int,
    ) -> tuple[str, dict[str, Any], dict[str, RuntimeFieldDescriptor]]:
        """Строит SQL-фрагмент WHERE для одного runtime-фильтра.

        Значения фильтров приводятся через RuntimeFieldTypePolicy, а поля json/jsonb
        возвращаются в bind_fields, чтобы `_statement` мог назначить тип bindparam.
        """
        field = descriptor.field_by_name(filter_spec.field)
        if field is None:
            raise RuntimeDataFilterError(
                code="UNKNOWN_FILTER_FIELD",
                message=f"Unknown filter field '{filter_spec.field}'.",
                details={
                    "field": filter_spec.field,
                },
            )

        op = filter_spec.op
        field_sql = self._qi(field.name)

        if op == "eq":
            if filter_spec.value is None:
                return (f"{field_sql} IS NULL", {}, {})
            coerced = self._type_policy.coerce_value_for_field(
                field=field,
                raw_value=filter_spec.value,
            )
            param_name = f"f_{position}"
            return (
                f"{field_sql} = :{param_name}",
                {param_name: coerced},
                {param_name: field},
            )

        if op == "neq":
            if filter_spec.value is None:
                return (f"{field_sql} IS NOT NULL", {}, {})
            coerced = self._type_policy.coerce_value_for_field(
                field=field,
                raw_value=filter_spec.value,
            )
            param_name = f"f_{position}"
            return (
                f"{field_sql} <> :{param_name}",
                {param_name: coerced},
                {param_name: field},
            )

        if op == "in":
            if not isinstance(filter_spec.value, Sequence) or isinstance(
                filter_spec.value,
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
            items = list(filter_spec.value)
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
                params[param_name] = self._type_policy.coerce_value_for_field(
                    field=field,
                    raw_value=item,
                )
                bind_fields[param_name] = field
            return (f"{field_sql} IN ({', '.join(placeholders)})", params, bind_fields)

        if op == "contains":
            if field.type_code != "text":
                raise RuntimeDataFilterError(
                    code="UNSUPPORTED_OPERATOR_FOR_FIELD_TYPE",
                    message=(
                        f"Filter 'contains' supports only text fields, "
                        f"got '{field.name}'."
                    ),
                    details={
                        "field": field.name,
                        "field_type": field.type_code,
                        "operator": op,
                    },
                )
            value = self._type_policy.coerce_value_for_field(
                field=field,
                raw_value=filter_spec.value,
            )
            param_name = f"f_{position}"
            return (
                f"CAST({field_sql} AS text) ILIKE :{param_name} ESCAPE '\\'",
                {param_name: f"%{self._escape_like_value(value)}%"},
                {},
            )

        if op in {"starts_with", "ends_with"}:
            if field.type_code != "text":
                raise RuntimeDataFilterError(
                    code="UNSUPPORTED_OPERATOR_FOR_FIELD_TYPE",
                    message=(
                        f"Filter '{op}' supports only text fields, "
                        f"got '{field.name}'."
                    ),
                    details={
                        "field": field.name,
                        "field_type": field.type_code,
                        "operator": op,
                    },
                )
            value = self._type_policy.coerce_value_for_field(
                field=field,
                raw_value=filter_spec.value,
            )
            escaped_value = self._escape_like_value(value)
            pattern = (
                f"{escaped_value}%" if op == "starts_with" else f"%{escaped_value}"
            )
            param_name = f"f_{position}"
            return (
                f"CAST({field_sql} AS text) ILIKE :{param_name} ESCAPE '\\'",
                {param_name: pattern},
                {},
            )

        if op in {"gt", "gte", "lt", "lte"}:
            coerced = self._type_policy.coerce_value_for_field(
                field=field,
                raw_value=filter_spec.value,
            )
            param_name = f"f_{position}"
            comparison = {
                "gt": ">",
                "gte": ">=",
                "lt": "<",
                "lte": "<=",
            }[op]
            return (
                f"{field_sql} {comparison} :{param_name}",
                {param_name: coerced},
                {param_name: field},
            )

        if op == "between":
            if not isinstance(filter_spec.value, Sequence) or isinstance(
                filter_spec.value,
                (str, bytes),
            ):
                raise RuntimeDataFilterError(
                    code="INVALID_FILTER_VALUE_TYPE",
                    message=(
                        f"Filter '{field.name}' with operator 'between' "
                        "requires a two-item sequence."
                    ),
                    details={
                        "field": field.name,
                        "operator": op,
                    },
                )
            items = list(filter_spec.value)
            if len(items) != 2:
                raise RuntimeDataFilterError(
                    code="INVALID_FILTER_VALUE_TYPE",
                    message=(
                        f"Filter '{field.name}' with operator 'between' "
                        "requires exactly two values."
                    ),
                    details={
                        "field": field.name,
                        "operator": op,
                        "expected_length": 2,
                        "actual_length": len(items),
                    },
                )
            start_param = f"f_{position}_start"
            end_param = f"f_{position}_end"
            return (
                f"{field_sql} BETWEEN :{start_param} AND :{end_param}",
                {
                    start_param: self._type_policy.coerce_value_for_field(
                        field=field,
                        raw_value=items[0],
                    ),
                    end_param: self._type_policy.coerce_value_for_field(
                        field=field,
                        raw_value=items[1],
                    ),
                },
                {
                    start_param: field,
                    end_param: field,
                },
            )

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

    def _build_sort_clause(
        self,
        *,
        descriptor: RuntimeObjectDescriptor,
        sorting: Sequence[SortSpec],
    ) -> str:
        """Строит ORDER BY по валидированным полям descriptor."""
        if not sorting:
            return ""

        sort_chunks: list[str] = []
        for sort_spec in sorting:
            field = descriptor.field_by_name(sort_spec.field)
            if field is None:
                raise RuntimeDataFilterError(
                    code="UNKNOWN_SORT_FIELD",
                    message=f"Unknown sort field '{sort_spec.field}'.",
                    details={
                        "field": sort_spec.field,
                    },
                )
            direction = sort_spec.direction.lower()
            if direction not in {"asc", "desc"}:
                raise RuntimeDataFilterError(
                    code="INVALID_SORT_DSL",
                    message=f"Unsupported sort direction '{sort_spec.direction}'.",
                    details={
                        "field": sort_spec.field,
                        "direction": sort_spec.direction,
                    },
                )
            sort_chunks.append(f"{self._qi(field.name)} {direction.upper()}")

        return f"ORDER BY {', '.join(sort_chunks)}"

    def _selectable_columns(
        self,
        *,
        descriptor: RuntimeObjectDescriptor,
        fetch_plan: FetchPlan | None,
    ) -> list[str]:
        """Возвращает список SELECT-колонок и всегда добавляет pk к projection."""
        projections = fetch_plan.projections if fetch_plan is not None else ()
        if not projections:
            fields = [field.name for field in descriptor.fields]
            return [self._qi(field) for field in fields]

        selected: list[str] = []
        seen: set[str] = set()
        for field_name in projections:
            field = descriptor.field_by_name(field_name)
            if field is None:
                raise RuntimeDataValidationError(
                    f"Unknown projection field '{field_name}'."
                )
            if field.name in seen:
                continue
            selected.append(field.name)
            seen.add(field.name)

        if descriptor.pk not in seen:
            selected.append(descriptor.pk)
        return [self._qi(field_name) for field_name in selected]

    async def _execute(
        self,
        sql: str,
        params: Mapping[str, Any] | None = None,
        *,
        bind_fields: Mapping[str, RuntimeFieldDescriptor] | None = None,
    ):
        """Выполняет SQLAlchemy statement и переводит persistence-ошибки в доменные."""
        statement = self._statement(sql, bind_fields or {})
        try:
            if params is None:
                return await self._session.execute(statement)
            return await self._session.execute(statement, params)
        except SQLAlchemyError as exc:
            raise RuntimeDataPersistenceError(
                "Runtime data persistence failed; schema metadata may be incompatible "
                "with the physical database."
            ) from exc

    def _statement(
        self,
        sql: str,
        bind_fields: Mapping[str, RuntimeFieldDescriptor],
    ) -> TextClause:
        """Создает TextClause и назначает JSONB bindparam для json/multiselect полей."""
        statement = text(sql)
        typed_params = [
            bindparam(param_name, type_=postgresql.JSONB())
            for param_name, field in bind_fields.items()
            if field.type_code in {"json", "multiselect"}
        ]
        if typed_params:
            statement = statement.bindparams(*typed_params)
        return statement

    @staticmethod
    def _required_field(
        descriptor: RuntimeObjectDescriptor,
        field_name: str,
    ) -> RuntimeFieldDescriptor:
        """Возвращает обязательное поле descriptor или поднимает policy error."""
        field = descriptor.field_by_name(field_name)
        if field is None:
            raise RuntimeDataPolicyError(
                f"Descriptor does not contain required field '{field_name}'."
            )
        return field

    def _ensure_descriptor(self, descriptor: RuntimeObjectDescriptor) -> None:
        """Проверяет SQL-идентификаторы descriptor перед динамическим SQL."""
        self._validate_identifier(descriptor.schema_name, "schema_name")
        self._validate_identifier(descriptor.table_name, "table_name")
        self._required_field(descriptor, descriptor.pk)
        for field in descriptor.fields:
            self._validate_identifier(field.name, "field")

    @classmethod
    def _validate_identifier(cls, value: str, title: str) -> None:
        """Проверяет, что identifier безопасен для использования в SQL."""
        normalized = value.strip()
        if not _IDENTIFIER_RE.fullmatch(normalized):
            raise RuntimeDataPolicyError(f"Invalid {title} identifier '{value}'.")

    @classmethod
    def _qualified_table(cls, descriptor: RuntimeObjectDescriptor) -> str:
        """Возвращает quoted schema.table для descriptor."""
        return f"{cls._qi(descriptor.schema_name)}.{cls._qi(descriptor.table_name)}"

    @staticmethod
    def _qi(identifier: str) -> str:
        """Кавычит PostgreSQL-идентификатор."""
        return f'"{identifier}"'

    @staticmethod
    def _escape_like_value(value: str) -> str:
        """Escapes user text for PostgreSQL LIKE patterns with backslash ESCAPE."""
        return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


class PostgresRuntimeRelationLoader(RuntimeRelationLoader):
    """PostgreSQL loader relation-данных по RuntimeRelationDescriptor."""

    def __init__(self, session: AsyncSession) -> None:
        """Инициализирует loader SQLAlchemy-сессией."""
        self._session = session

    async def load(
        self,
        *,
        descriptor: RuntimeObjectDescriptor,
        rows: Sequence[Mapping[str, Any]],
        fetch_plan: FetchPlan,
    ) -> list[Mapping[str, Any]]:
        """Обогащает строки relation payload под API relation names."""
        result_rows = [dict(row) for row in rows]
        if not result_rows:
            return result_rows
        for relation_name in fetch_plan.relations:
            relation = self._find_relation(descriptor, relation_name)
            if relation is None:
                raise RuntimeDataValidationError(
                    f"Unknown relation '{relation_name}' for object '{descriptor.object_name}'."
                )
            if relation.relation_type == "many_to_many":
                await self._load_many_to_many(
                    descriptor=descriptor,
                    rows=result_rows,
                    relation=relation,
                )
            elif relation.relation_type == "one_to_many":
                await self._load_one_to_many(
                    descriptor=descriptor,
                    rows=result_rows,
                    relation=relation,
                )
            elif relation.relation_type in {"many_to_one", "one_to_one"}:
                await self._load_fk_relation(
                    descriptor=descriptor,
                    rows=result_rows,
                    relation=relation,
                )
            else:
                raise RuntimeDataValidationError(
                    f"Unsupported relation_type '{relation.relation_type}'."
                )
        return result_rows

    async def _load_fk_relation(
        self,
        *,
        descriptor: RuntimeObjectDescriptor,
        rows: list[dict[str, Any]],
        relation: RuntimeRelationDescriptor,
    ) -> None:
        if relation.fk_field is None or relation.referenced_field is None:
            raise RuntimeDataValidationError(
                f"Relation '{relation.name}' has incomplete FK metadata."
            )
        if descriptor.table_name == relation.owning_object:
            related_table = relation.referenced_object
            output_name = (
                relation.source_relation_name
                if descriptor.table_name == relation.source_object
                else relation.target_relation_name
            )
            fk_values = [row.get(relation.fk_field) for row in rows]
            values = [value for value in fk_values if value is not None]
            related_by_id = await self._select_by_column(
                schema_name=descriptor.schema_name,
                table_name=related_table or "",
                column_name=relation.referenced_field,
                values=values,
            )
            for row in rows:
                row[output_name] = related_by_id.get(row.get(relation.fk_field))
            return

        if relation.owning_object is None:
            raise RuntimeDataValidationError(
                f"Relation '{relation.name}' has no owning object."
            )
        output_name = relation.target_relation_name
        owner_ids = [row.get(descriptor.pk) for row in rows]
        related_rows = await self._select_by_column_list(
            schema_name=descriptor.schema_name,
            table_name=relation.owning_object,
            column_name=relation.fk_field,
            values=[value for value in owner_ids if value is not None],
        )
        grouped: dict[Any, list[dict[str, Any]]] = {}
        for related in related_rows:
            grouped.setdefault(related.get(relation.fk_field), []).append(related)
        for row in rows:
            items = grouped.get(row.get(descriptor.pk), [])
            row[output_name] = (
                items
                if relation.relation_type == "many_to_one"
                else (items[0] if items else None)
            )

    async def _load_one_to_many(
        self,
        *,
        descriptor: RuntimeObjectDescriptor,
        rows: list[dict[str, Any]],
        relation: RuntimeRelationDescriptor,
    ) -> None:
        if relation.fk_field is None or relation.referenced_field is None:
            raise RuntimeDataValidationError(
                f"Relation '{relation.name}' has incomplete FK metadata."
            )
        if descriptor.table_name == relation.source_object:
            owner_ids = [row.get(descriptor.pk) for row in rows]
            children = await self._select_by_column_list(
                schema_name=descriptor.schema_name,
                table_name=relation.target_object,
                column_name=relation.fk_field,
                values=[value for value in owner_ids if value is not None],
            )
            grouped: dict[Any, list[dict[str, Any]]] = {}
            for child in children:
                grouped.setdefault(child.get(relation.fk_field), []).append(child)
            for row in rows:
                row[relation.source_relation_name] = grouped.get(
                    row.get(descriptor.pk),
                    [],
                )
            return

        fk_values = [row.get(relation.fk_field) for row in rows]
        parents = await self._select_by_column(
            schema_name=descriptor.schema_name,
            table_name=relation.source_object,
            column_name=relation.referenced_field,
            values=[value for value in fk_values if value is not None],
        )
        for row in rows:
            row[relation.target_relation_name] = parents.get(row.get(relation.fk_field))

    async def _load_many_to_many(
        self,
        *,
        descriptor: RuntimeObjectDescriptor,
        rows: list[dict[str, Any]],
        relation: RuntimeRelationDescriptor,
    ) -> None:
        if (
            relation.relation_table_name is None
            or relation.source_join_column_name is None
            or relation.target_join_column_name is None
        ):
            raise RuntimeDataValidationError(
                f"Relation '{relation.name}' has incomplete M2M metadata."
            )
        if descriptor.table_name == relation.source_object:
            owner_column = relation.source_join_column_name
            related_column = relation.target_join_column_name
            related_table = relation.target_object
            output_name = relation.source_relation_name
        else:
            owner_column = relation.target_join_column_name
            related_column = relation.source_join_column_name
            related_table = relation.source_object
            output_name = relation.target_relation_name
        owner_ids = [
            row.get(descriptor.pk) for row in rows if row.get(descriptor.pk) is not None
        ]
        related_rows = await self._select_many_to_many(
            schema_name=descriptor.schema_name,
            relation_table_name=relation.relation_table_name,
            owner_column=owner_column,
            related_column=related_column,
            related_table=related_table,
            owner_ids=owner_ids,
        )
        grouped: dict[Any, list[dict[str, Any]]] = {}
        for related in related_rows:
            owner_id = related.pop("__owner_id")
            grouped.setdefault(owner_id, []).append(related)
        for row in rows:
            row[output_name] = grouped.get(row.get(descriptor.pk), [])

    async def _select_by_column(
        self,
        *,
        schema_name: str,
        table_name: str,
        column_name: str,
        values: Sequence[Any],
    ) -> dict[Any, dict[str, Any]]:
        rows = await self._select_by_column_list(
            schema_name=schema_name,
            table_name=table_name,
            column_name=column_name,
            values=values,
        )
        return {row.get(column_name): row for row in rows}

    async def _select_by_column_list(
        self,
        *,
        schema_name: str,
        table_name: str,
        column_name: str,
        values: Sequence[Any],
    ) -> list[dict[str, Any]]:
        if not values:
            return []
        params = {f"value_{index}": value for index, value in enumerate(values)}
        placeholders = ", ".join(f":{name}" for name in params)
        sql = (
            f"SELECT * FROM {self._qualified_table(schema_name, table_name)} "
            f"WHERE {self._qi(column_name)} IN ({placeholders})"
        )
        result = await self._execute(sql, params)
        return [dict(row) for row in result.mappings().all()]

    async def _select_many_to_many(
        self,
        *,
        schema_name: str,
        relation_table_name: str,
        owner_column: str,
        related_column: str,
        related_table: str,
        owner_ids: Sequence[Any],
    ) -> list[dict[str, Any]]:
        if not owner_ids:
            return []
        params = {f"owner_{index}": value for index, value in enumerate(owner_ids)}
        placeholders = ", ".join(f":{name}" for name in params)
        relation_ref = self._qualified_table(schema_name, relation_table_name)
        related_ref = self._qualified_table(schema_name, related_table)
        sql = (
            f"SELECT rel.{self._qi(owner_column)} AS __owner_id, related.* "
            f"FROM {relation_ref} rel "
            f"JOIN {related_ref} related "
            f"ON related.{self._qi('id')} = rel.{self._qi(related_column)} "
            f"WHERE rel.{self._qi(owner_column)} IN ({placeholders})"
        )
        result = await self._execute(sql, params)
        return [dict(row) for row in result.mappings().all()]

    async def _execute(self, sql: str, params: Mapping[str, Any]):
        try:
            return await self._session.execute(text(sql), params)
        except SQLAlchemyError as exc:
            raise RuntimeDataPersistenceError(
                "Runtime relation loading failed; metadata may be incompatible "
                "with physical database."
            ) from exc

    @staticmethod
    def _find_relation(
        descriptor: RuntimeObjectDescriptor,
        relation_name: str,
    ) -> RuntimeRelationDescriptor | None:
        normalized = relation_name.strip()
        for relation in descriptor.relations:
            if normalized in {
                relation.name,
                relation.source_relation_name,
                relation.target_relation_name,
            }:
                return relation
        return None

    @classmethod
    def _qualified_table(cls, schema_name: str, table_name: str) -> str:
        cls._validate_identifier(schema_name, "schema_name")
        cls._validate_identifier(table_name, "table_name")
        return f"{cls._qi(schema_name)}.{cls._qi(table_name)}"

    @classmethod
    def _validate_identifier(cls, value: str, title: str) -> None:
        if not _IDENTIFIER_RE.fullmatch(value.strip()):
            raise RuntimeDataPolicyError(f"Invalid {title} identifier '{value}'.")

    @staticmethod
    def _qi(identifier: str) -> str:
        return f'"{identifier}"'


class NoopRuntimeRelationLoader(RuntimeRelationLoader):
    """Relation loader-заглушка для тестов и альтернативных backends."""

    async def load(
        self,
        *,
        descriptor: RuntimeObjectDescriptor,
        rows: Sequence[Mapping[str, Any]],
        fetch_plan: FetchPlan,
    ) -> list[Mapping[str, Any]]:
        """Возвращает копии runtime-строк, игнорируя relation fetch plan."""
        _ = descriptor
        _ = fetch_plan
        return [dict(row) for row in rows]


class PostgresRuntimeRelationCommandGateway(RuntimeRelationCommandGateway):
    """PostgreSQL gateway для операций над runtime relations."""

    def __init__(self, session: AsyncSession) -> None:
        """Инициализирует relation command gateway."""
        self._session = session
        self._loader = PostgresRuntimeRelationLoader(session=session)

    async def get_related_record(
        self,
        *,
        descriptor: RuntimeObjectDescriptor,
        relation_name: str,
        object_id: Any,
    ) -> Mapping[str, Any] | None:
        """Возвращает single related record или None."""
        items = await self.list_related_records(
            descriptor=descriptor,
            relation_name=relation_name,
            object_id=object_id,
        )
        return items[0] if items else None

    async def list_related_records(
        self,
        *,
        descriptor: RuntimeObjectDescriptor,
        relation_name: str,
        object_id: Any,
    ) -> list[Mapping[str, Any]]:
        """Возвращает related records через relation loader."""
        relation = self._required_relation(descriptor, relation_name)
        row = await self._select_base_row(
            descriptor=descriptor,
            object_id=object_id,
        )
        if row is None:
            return []
        loaded = await self._loader.load(
            descriptor=descriptor,
            rows=[row],
            fetch_plan=FetchPlan(relations=(relation_name,)),
        )
        value = loaded[0].get(self._output_name(descriptor, relation))
        if value is None:
            return []
        if isinstance(value, list):
            return value
        return [value]

    async def attach_related_record(
        self,
        *,
        descriptor: RuntimeObjectDescriptor,
        relation_name: str,
        object_id: Any,
        related_id: Any,
    ) -> None:
        """Создает M2M relation row идемпотентно."""
        relation = self._required_relation(descriptor, relation_name)
        if relation.relation_type != "many_to_many":
            raise RuntimeDataValidationError("attach supports only many_to_many.")
        source_id, target_id = self._m2m_source_target_ids(
            descriptor=descriptor,
            relation=relation,
            object_id=object_id,
            related_id=related_id,
        )
        sql = (
            f"INSERT INTO {self._relation_table_ref(descriptor, relation)} "
            f"({self._qi('id')}, {self._qi(relation.source_join_column_name or '')}, "
            f"{self._qi(relation.target_join_column_name or '')}, {self._qi('created_at')}) "
            "VALUES (gen_random_uuid(), :source_id, :target_id, CURRENT_TIMESTAMP) "
            f"ON CONFLICT ({self._qi(relation.source_join_column_name or '')}, "
            f"{self._qi(relation.target_join_column_name or '')}) DO NOTHING"
        )
        await self._execute(sql, {"source_id": source_id, "target_id": target_id})

    async def detach_related_record(
        self,
        *,
        descriptor: RuntimeObjectDescriptor,
        relation_name: str,
        object_id: Any,
        related_id: Any,
    ) -> None:
        """Удаляет M2M relation row."""
        relation = self._required_relation(descriptor, relation_name)
        if relation.relation_type != "many_to_many":
            raise RuntimeDataValidationError("detach supports only many_to_many.")
        source_id, target_id = self._m2m_source_target_ids(
            descriptor=descriptor,
            relation=relation,
            object_id=object_id,
            related_id=related_id,
        )
        sql = (
            f"DELETE FROM {self._relation_table_ref(descriptor, relation)} "
            f"WHERE {self._qi(relation.source_join_column_name or '')} = :source_id "
            f"AND {self._qi(relation.target_join_column_name or '')} = :target_id"
        )
        await self._execute(sql, {"source_id": source_id, "target_id": target_id})

    async def set_relation(
        self,
        *,
        descriptor: RuntimeObjectDescriptor,
        relation_name: str,
        object_id: Any,
        related_id: Any,
    ) -> None:
        """Устанавливает FK value на owning side."""
        relation = self._required_relation(descriptor, relation_name)
        if relation.relation_type == "many_to_many":
            raise RuntimeDataValidationError("set_relation does not support M2M.")
        table_name, row_id, fk_value = self._fk_update_target(
            descriptor=descriptor,
            relation=relation,
            object_id=object_id,
            related_id=related_id,
        )
        sql = (
            f"UPDATE {self._qualified_table(descriptor.schema_name, table_name)} "
            f"SET {self._qi(relation.fk_field or '')} = :fk_value "
            f"WHERE {self._qi('id')} = :row_id"
        )
        await self._execute(sql, {"fk_value": fk_value, "row_id": row_id})

    async def unset_relation(
        self,
        *,
        descriptor: RuntimeObjectDescriptor,
        relation_name: str,
        object_id: Any,
        related_id: Any | None = None,
    ) -> None:
        """Сбрасывает FK value на owning side."""
        relation = self._required_relation(descriptor, relation_name)
        if relation.relation_type == "many_to_many":
            raise RuntimeDataValidationError("unset_relation does not support M2M.")
        if relation.is_required:
            raise RuntimeDataValidationError("Required relation cannot be unset.")
        if descriptor.table_name == relation.owning_object:
            table_name = descriptor.table_name
            row_id = object_id
        else:
            if related_id is None:
                raise RuntimeDataValidationError(
                    "related_id is required when unsetting relation from referenced side."
                )
            table_name = relation.owning_object or ""
            row_id = related_id
        sql = (
            f"UPDATE {self._qualified_table(descriptor.schema_name, table_name)} "
            f"SET {self._qi(relation.fk_field or '')} = NULL "
            f"WHERE {self._qi('id')} = :row_id"
        )
        await self._execute(sql, {"row_id": row_id})

    async def _select_base_row(
        self,
        *,
        descriptor: RuntimeObjectDescriptor,
        object_id: Any,
    ) -> dict[str, Any] | None:
        sql = (
            f"SELECT * FROM {self._qualified_table(descriptor.schema_name, descriptor.table_name)} "
            f"WHERE {self._qi(descriptor.pk)} = :object_id LIMIT 1"
        )
        result = await self._execute(sql, {"object_id": object_id})
        row = result.mappings().first()
        return None if row is None else dict(row)

    @staticmethod
    def _required_relation(
        descriptor: RuntimeObjectDescriptor,
        relation_name: str,
    ) -> RuntimeRelationDescriptor:
        relation = PostgresRuntimeRelationLoader._find_relation(
            descriptor,
            relation_name,
        )
        if relation is None:
            raise RuntimeDataValidationError(
                f"Unknown relation '{relation_name}' for object '{descriptor.object_name}'."
            )
        return relation

    @staticmethod
    def _output_name(
        descriptor: RuntimeObjectDescriptor,
        relation: RuntimeRelationDescriptor,
    ) -> str:
        if descriptor.table_name == relation.source_object:
            return relation.source_relation_name
        return relation.target_relation_name

    @staticmethod
    def _m2m_source_target_ids(
        *,
        descriptor: RuntimeObjectDescriptor,
        relation: RuntimeRelationDescriptor,
        object_id: Any,
        related_id: Any,
    ) -> tuple[Any, Any]:
        if descriptor.table_name == relation.source_object:
            return object_id, related_id
        return related_id, object_id

    @staticmethod
    def _fk_update_target(
        *,
        descriptor: RuntimeObjectDescriptor,
        relation: RuntimeRelationDescriptor,
        object_id: Any,
        related_id: Any,
    ) -> tuple[str, Any, Any]:
        if descriptor.table_name == relation.owning_object:
            return descriptor.table_name, object_id, related_id
        return relation.owning_object or "", related_id, object_id

    @classmethod
    def _relation_table_ref(
        cls,
        descriptor: RuntimeObjectDescriptor,
        relation: RuntimeRelationDescriptor,
    ) -> str:
        if (
            relation.relation_table_name is None
            or relation.source_join_column_name is None
            or relation.target_join_column_name is None
        ):
            raise RuntimeDataValidationError("M2M relation metadata is incomplete.")
        return cls._qualified_table(
            descriptor.schema_name, relation.relation_table_name
        )

    async def _execute(self, sql: str, params: Mapping[str, Any]):
        try:
            return await self._session.execute(text(sql), params)
        except SQLAlchemyError as exc:
            raise RuntimeDataPersistenceError(
                "Runtime relation command failed; metadata may be incompatible "
                "with physical database."
            ) from exc

    @classmethod
    def _qualified_table(cls, schema_name: str, table_name: str) -> str:
        PostgresRuntimeRelationLoader._validate_identifier(schema_name, "schema_name")
        PostgresRuntimeRelationLoader._validate_identifier(table_name, "table_name")
        return f"{cls._qi(schema_name)}.{cls._qi(table_name)}"

    @staticmethod
    def _qi(identifier: str) -> str:
        return f'"{identifier}"'
