from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Protocol

from src.modules.shared import EntityIdVO


class RuntimeFilterValidatorProtocol(Protocol):
    """Port for validating runtime_data filter DSL against an object."""

    async def validate_filter(
        self,
        *,
        tenant_id: EntityIdVO,
        object_name: str,
        filter_config: Mapping[str, Any],
        path: str,
    ) -> None:
        """Validate filter config or raise a controlled segment DSL error."""
        ...


__all__ = ["RuntimeFilterValidatorProtocol"]
