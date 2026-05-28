from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from typing import Any

from src.modules.runtime_data.application.models import TypedFilterExpression
from src.modules.runtime_data.application.query.filter_dsl.parser import (
    FilterDslParser,
)
from src.modules.runtime_data.application.query.filter_dsl.semantic_validator import (
    FilterSemanticValidator,
)
from src.modules.schema_registry.runtime import RuntimeObjectDescriptor


def dump_segment_version_filter_for_runtime(
    filter_config: Mapping[str, Any],
) -> dict[str, Any]:
    """Return a JSON-like copy of DSL filter config for runtime_data adapters."""
    return deepcopy(dict(filter_config))


def build_runtime_filter_specs(
    *,
    descriptor: RuntimeObjectDescriptor,
    filter_config: Mapping[str, Any],
    parser: FilterDslParser | None = None,
    semantic_validator: FilterSemanticValidator | None = None,
) -> tuple[TypedFilterExpression, ...]:
    """Convert segment DSL filter JSON into runtime_data typed filter specs."""
    filter_parser = parser or FilterDslParser()
    validator = semantic_validator or FilterSemanticValidator()
    filter_ast = filter_parser.parse(filter_config)
    if not filter_ast:
        return ()
    return validator.validate(
        descriptor=descriptor,
        filter_ast=filter_ast,
    )


__all__ = [
    "build_runtime_filter_specs",
    "dump_segment_version_filter_for_runtime",
]
