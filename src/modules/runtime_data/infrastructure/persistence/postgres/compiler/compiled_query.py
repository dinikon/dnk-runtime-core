from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from src.modules.schema_registry.runtime import RuntimeFieldDescriptor


@dataclass(frozen=True, slots=True)
class CompiledQuery:
    """SQL text plus bind params produced by infrastructure compilers."""

    sql: str
    params: Mapping[str, Any] = field(default_factory=dict)
    bind_fields: Mapping[str, RuntimeFieldDescriptor] = field(default_factory=dict)


__all__ = ["CompiledQuery"]
