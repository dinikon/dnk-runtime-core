from __future__ import annotations

from dataclasses import dataclass
import re

from src.modules.schema_registry.domain.error import InvalidValueObjectError
from src.modules.schema_registry.domain.object_feature.value_object.object_feature_code import (
    ObjectFeatureCode,
)

_FEATURE_CODE_RE = re.compile(r"^[A-Z][A-Z0-9_]*$")


@dataclass(frozen=True, slots=True)
class FeatureCodeVO:
    """Value object кода feature runtime-объекта."""

    value: str

    def __post_init__(self) -> None:
        """Нормализует и валидирует feature code."""
        normalized = self.value.strip().upper()

        if not normalized:
            raise InvalidValueObjectError("Feature code cannot be empty.")

        if len(normalized) > 63:
            raise InvalidValueObjectError("Feature code is too long. Max length is 63.")

        if not _FEATURE_CODE_RE.match(normalized):
            raise InvalidValueObjectError(
                "Feature code must match pattern ^[A-Z][A-Z0-9_]*$."
            )

        try:
            feature_code = ObjectFeatureCode.from_value(normalized)
        except ValueError as exc:
            allowed = ", ".join(item.value for item in ObjectFeatureCode)
            raise InvalidValueObjectError(
                f"Unsupported feature code '{normalized}'. Allowed: {allowed}."
            ) from exc

        object.__setattr__(self, "value", feature_code.value)
