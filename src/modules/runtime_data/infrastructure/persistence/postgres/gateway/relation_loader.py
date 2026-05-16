from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, List

from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.runtime_data.application.models import FetchPlan
from src.modules.runtime_data.application.ports import RuntimeRelationLoader
from src.modules.runtime_data.domain import RuntimeDataValidationError
from src.modules.runtime_data.infrastructure.persistence.postgres.compiler.identifier import (
    qualified_table,
    quote_identifier,
)
from src.modules.runtime_data.infrastructure.persistence.postgres.execution import (
    PostgresSqlExecutor,
)
from src.modules.schema_registry.runtime import (
    RuntimeObjectDescriptor,
    RuntimeRelationDescriptor,
)

_RELATION_LOAD_ERROR_MESSAGE = (
    "Runtime relation loading failed; metadata may be incompatible "
    "with physical database."
)


class PostgresRuntimeRelationLoader(RuntimeRelationLoader):
    """PostgreSQL loader relation-данных по RuntimeRelationDescriptor."""

    def __init__(
        self,
        session: AsyncSession,
        *,
        executor: PostgresSqlExecutor | None = None,
    ) -> None:
        self._session = session
        self._executor = executor or PostgresSqlExecutor(
            session,
            error_message=_RELATION_LOAD_ERROR_MESSAGE,
        )

    async def load(
        self,
        *,
        descriptor: RuntimeObjectDescriptor,
        rows: Sequence[Mapping[str, Any]],
        fetch_plan: FetchPlan,
    ) -> list[Mapping[str, Any]]:
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
    ) -> List[dict[str, Any]]:
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
        return await self._executor.execute(sql, params)

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
        return qualified_table(schema_name, table_name)

    @staticmethod
    def _qi(identifier: str) -> str:
        return quote_identifier(identifier)


class NoopRuntimeRelationLoader(RuntimeRelationLoader):
    """Relation loader-заглушка для тестов и альтернативных backends."""

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


__all__ = [
    "NoopRuntimeRelationLoader",
    "PostgresRuntimeRelationLoader",
]
