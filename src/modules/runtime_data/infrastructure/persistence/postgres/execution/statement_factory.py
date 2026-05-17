from __future__ import annotations

from collections.abc import Mapping

from sqlalchemy import bindparam, text
from sqlalchemy.dialects import postgresql
from sqlalchemy.sql.elements import TextClause

from src.modules.schema_registry.runtime import RuntimeFieldDescriptor


class PostgresStatementFactory:
    """Builds SQLAlchemy text statements with runtime-aware bind types."""

    def statement(
        self,
        sql: str,
        bind_fields: Mapping[str, RuntimeFieldDescriptor],
    ) -> TextClause:
        """Create TextClause and bind JSONB params for json/multiselect fields."""
        statement = text(sql)
        typed_params = [
            bindparam(param_name, type_=postgresql.JSONB())
            for param_name, field in bind_fields.items()
            if field.type_code in {"json", "multiselect"}
        ]
        if typed_params:
            statement = statement.bindparams(*typed_params)
        return statement


__all__ = ["PostgresStatementFactory"]
