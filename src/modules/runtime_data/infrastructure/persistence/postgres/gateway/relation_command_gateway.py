from __future__ import annotations

from collections.abc import Mapping
from typing import Any, List

from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.runtime_data.application.models import FetchPlan
from src.modules.runtime_data.application.ports import RuntimeRelationCommandGateway
from src.modules.runtime_data.domain import RuntimeDataValidationError
from src.modules.runtime_data.infrastructure.persistence.postgres.compiler.identifier import (
    qualified_table,
    quote_identifier,
)
from src.modules.runtime_data.infrastructure.persistence.postgres.execution import (
    PostgresSqlExecutor,
)
from src.modules.runtime_data.infrastructure.persistence.postgres.gateway.relation_loader import (
    PostgresRuntimeRelationLoader,
)
from src.modules.schema_registry.runtime import (
    RuntimeObjectDescriptor,
    RuntimeRelationDescriptor,
)

_RELATION_COMMAND_ERROR_MESSAGE = (
    "Runtime relation command failed; metadata may be incompatible "
    "with physical database."
)


class PostgresRuntimeRelationCommandGateway(RuntimeRelationCommandGateway):
    """PostgreSQL gateway для операций над runtime relations."""

    def __init__(
        self,
        session: AsyncSession,
        *,
        executor: PostgresSqlExecutor | None = None,
        relation_loader: PostgresRuntimeRelationLoader | None = None,
    ) -> None:
        self._session = session
        self._executor = executor or PostgresSqlExecutor(
            session,
            error_message=_RELATION_COMMAND_ERROR_MESSAGE,
        )
        self._loader = relation_loader or PostgresRuntimeRelationLoader(
            session=session,
        )

    async def get_related_record(
        self,
        *,
        descriptor: RuntimeObjectDescriptor,
        relation_name: str,
        object_id: Any,
    ) -> Mapping[str, Any] | None:
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
    ) -> List[Mapping[str, Any]]:
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
        return await self._executor.execute(sql, params)

    @classmethod
    def _qualified_table(cls, schema_name: str, table_name: str) -> str:
        return qualified_table(schema_name, table_name)

    @staticmethod
    def _qi(identifier: str) -> str:
        return quote_identifier(identifier)


__all__ = ["PostgresRuntimeRelationCommandGateway"]
