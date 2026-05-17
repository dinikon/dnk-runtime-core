from __future__ import annotations

from collections.abc import Sequence

from src.modules.runtime_data.application.models import SortSpec
from src.modules.runtime_data.domain.error import RuntimeDataFilterError
from src.modules.runtime_data.infrastructure.persistence.postgres.compiler.identifier import (
    quote_identifier,
)
from src.modules.schema_registry.runtime import RuntimeObjectDescriptor


class PostgresSortSqlCompiler:
    """Compiles validated runtime sort specs to ORDER BY SQL."""

    def compile(
        self,
        *,
        descriptor: RuntimeObjectDescriptor,
        sorting: Sequence[SortSpec],
    ) -> str:
        if not sorting:
            return ""

        sort_chunks: list[str] = []
        for sort_spec in sorting:
            field_descriptor = descriptor.field_by_name(sort_spec.field)
            if field_descriptor is None:
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
            sort_chunks.append(
                f"{quote_identifier(field_descriptor.name)} {direction.upper()}"
            )

        return f"ORDER BY {', '.join(sort_chunks)}"


__all__ = ["PostgresSortSqlCompiler"]
