from __future__ import annotations

from dataclasses import dataclass

from src.modules.runtime_data.application.models import (
    FetchPlan,
    PageSpec,
    SortSpec,
    TypedFilterExpression,
)
from src.modules.schema_registry.runtime import RuntimeObjectDescriptor


@dataclass(frozen=True, slots=True)
class RuntimeQueryPlan:
    """Descriptor-backed, semantically validated plan for runtime querying."""

    descriptor: RuntimeObjectDescriptor
    filters: tuple[TypedFilterExpression, ...]
    sorting: tuple[SortSpec, ...]
    page: PageSpec
    fetch_plan: FetchPlan | None = None


__all__ = ["RuntimeQueryPlan"]
