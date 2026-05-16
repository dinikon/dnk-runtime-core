from __future__ import annotations

from src.modules.runtime_data.domain import RuntimeDataFilterError


def filter_dsl_error(code: str, message: str) -> RuntimeDataFilterError:
    """Builds a stable runtime filter DSL error with a machine-readable prefix."""

    return RuntimeDataFilterError(f"{code}: {message}")


__all__ = ["filter_dsl_error"]
