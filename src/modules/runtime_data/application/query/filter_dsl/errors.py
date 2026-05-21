from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from src.modules.runtime_data.domain.error import RuntimeDataFilterError


def filter_dsl_error(
    code: str,
    message: str,
    *,
    details: Mapping[str, Any] | None = None,
) -> RuntimeDataFilterError:
    """Builds a stable runtime filter/sort DSL error with structured fields."""

    return RuntimeDataFilterError(
        code=code,
        message=message,
        details=dict(details or {}),
    )


__all__ = ["filter_dsl_error"]
