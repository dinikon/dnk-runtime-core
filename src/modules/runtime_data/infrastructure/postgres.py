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
    FilterSpec,
    PageSpec,
    SortSpec,
)
from src.modules.runtime_data.application.ports import (
    RuntimeCommandGateway,
    RuntimeQueryGateway,
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
)

_IDENTIFIER_RE = re.compile(r"^[a-z][a-z0-9_]*$")


class PostgresRuntimeGateway(RuntimeCommandGateway, RuntimeQueryGateway):
    def __init__(
        self,
        session: AsyncSession,
        type_policy: RuntimeFieldTypePolicy | None = None,
    ) -> None:
        self._session = session
        self._type_policy = type_policy or RuntimeFieldTypePolicy()

    async def insert(
        self,
        descriptor: RuntimeObjectDescriptor,
        payload: Mapping[str, Any],
    ) -> Mapping[str, Any]:
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

    async def get_by_id(
        self,
        *,
        descriptor: RuntimeObjectDescriptor,
        object_id: Any,
        fetch_plan: FetchPlan | None = None,
    ) -> Mapping[str, Any] | None:
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
        return self._type_policy.normalize_row(descriptor=descriptor, row=row)

    async def list(
        self,
        *,
        descriptor: RuntimeObjectDescriptor,
        filters: Sequence[FilterSpec] = (),
        sorting: Sequence[SortSpec] = (),
        page: PageSpec | None = None,
        fetch_plan: FetchPlan | None = None,
    ) -> list[Mapping[str, Any]]:
        self._ensure_descriptor(descriptor)
        columns = self._selectable_columns(descriptor=descriptor, fetch_plan=fetch_plan)

        params: dict[str, Any] = {}
        bind_fields: dict[str, RuntimeFieldDescriptor] = {}
        where_parts: list[str] = []
        for index, filter_spec in enumerate(filters):
            where_sql, where_params, where_bind_fields = self._build_filter_clause(
                descriptor=descriptor,
                filter_spec=filter_spec,
                position=index,
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
        return [
            self._type_policy.normalize_row(descriptor=descriptor, row=row)
            for row in rows
        ]

    def _build_filter_clause(
        self,
        *,
        descriptor: RuntimeObjectDescriptor,
        filter_spec: FilterSpec,
        position: int,
    ) -> tuple[str, dict[str, Any], dict[str, RuntimeFieldDescriptor]]:
        field = descriptor.field_by_name(filter_spec.field)
        if field is None:
            raise RuntimeDataFilterError(f"Unknown filter field '{filter_spec.field}'.")

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

        if op == "in":
            if not isinstance(filter_spec.value, Sequence) or isinstance(
                filter_spec.value,
                (str, bytes),
            ):
                raise RuntimeDataFilterError(
                    f"Filter '{field.name}' with operator 'in' requires a non-string sequence."
                )
            items = list(filter_spec.value)
            if not items:
                raise RuntimeDataFilterError(
                    f"Filter '{field.name}' with operator 'in' requires at least one value."
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
            if field.type_code not in {"text", "select"}:
                raise RuntimeDataFilterError(
                    f"Filter 'contains' supports only text/select fields, got '{field.name}'."
                )
            value = self._type_policy.coerce_value_for_field(
                field=field,
                raw_value=filter_spec.value,
            )
            param_name = f"f_{position}"
            return (
                f"CAST({field_sql} AS text) ILIKE :{param_name}",
                {param_name: f"%{value}%"},
                {},
            )

        if op in {"gte", "lte"}:
            coerced = self._type_policy.coerce_value_for_field(
                field=field,
                raw_value=filter_spec.value,
            )
            param_name = f"f_{position}"
            comparison = ">=" if op == "gte" else "<="
            return (
                f"{field_sql} {comparison} :{param_name}",
                {param_name: coerced},
                {param_name: field},
            )

        raise RuntimeDataFilterError(f"Unsupported filter operator '{op}'.")

    def _build_sort_clause(
        self,
        *,
        descriptor: RuntimeObjectDescriptor,
        sorting: Sequence[SortSpec],
    ) -> str:
        if not sorting:
            return ""

        sort_chunks: list[str] = []
        for sort_spec in sorting:
            field = descriptor.field_by_name(sort_spec.field)
            if field is None:
                raise RuntimeDataFilterError(f"Unknown sort field '{sort_spec.field}'.")
            direction = sort_spec.direction.lower()
            if direction not in {"asc", "desc"}:
                raise RuntimeDataFilterError(
                    f"Unsupported sort direction '{sort_spec.direction}'."
                )
            sort_chunks.append(f"{self._qi(field.name)} {direction.upper()}")

        return f"ORDER BY {', '.join(sort_chunks)}"

    def _selectable_columns(
        self,
        *,
        descriptor: RuntimeObjectDescriptor,
        fetch_plan: FetchPlan | None,
    ) -> list[str]:
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
        field = descriptor.field_by_name(field_name)
        if field is None:
            raise RuntimeDataPolicyError(
                f"Descriptor does not contain required field '{field_name}'."
            )
        return field

    def _ensure_descriptor(self, descriptor: RuntimeObjectDescriptor) -> None:
        self._validate_identifier(descriptor.schema_name, "schema_name")
        self._validate_identifier(descriptor.table_name, "table_name")
        self._required_field(descriptor, descriptor.pk)
        for field in descriptor.fields:
            self._validate_identifier(field.name, "field")

    @classmethod
    def _validate_identifier(cls, value: str, title: str) -> None:
        normalized = value.strip()
        if not _IDENTIFIER_RE.fullmatch(normalized):
            raise RuntimeDataPolicyError(f"Invalid {title} identifier '{value}'.")

    @classmethod
    def _qualified_table(cls, descriptor: RuntimeObjectDescriptor) -> str:
        return f"{cls._qi(descriptor.schema_name)}.{cls._qi(descriptor.table_name)}"

    @staticmethod
    def _qi(identifier: str) -> str:
        return f'"{identifier}"'


class NoopRuntimeRelationLoader(RuntimeRelationLoader):
    async def load(
        self,
        *,
        descriptor: RuntimeObjectDescriptor,
        rows: Sequence[Mapping[str, Any]],
        fetch_plan: FetchPlan,
    ) -> list[Mapping[str, Any]]:
        _ = descriptor
        _ = fetch_plan
        return [dict(row) for row in rows]
