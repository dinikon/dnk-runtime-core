from __future__ import annotations

from src.modules.runtime_data.application.models import FetchPlan
from src.modules.runtime_data.domain import RuntimeDataValidationError
from src.modules.runtime_data.infrastructure.persistence.postgres.compiler.identifier import (
    quote_identifier,
)
from src.modules.schema_registry.runtime import RuntimeObjectDescriptor


class PostgresProjectionSqlCompiler:
    """Compiles runtime projection metadata to SELECT column SQL."""

    def compile(
        self,
        *,
        descriptor: RuntimeObjectDescriptor,
        fetch_plan: FetchPlan | None,
    ) -> list[str]:
        projections = fetch_plan.projections if fetch_plan is not None else ()
        if not projections:
            return [quote_identifier(field.name) for field in descriptor.fields]

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
        return [quote_identifier(field_name) for field_name in selected]


__all__ = ["PostgresProjectionSqlCompiler"]
