from __future__ import annotations

from enum import StrEnum


class ObjectFeatureKind(StrEnum):
    """Классификация feature config по происхождению и поведению."""

    CUSTOM = "custom"
    STANDARD = "standard"
    SYSTEM = "system"

    @classmethod
    def from_value(
        cls,
        value: str | "ObjectFeatureKind",
    ) -> "ObjectFeatureKind":
        """Нормализует raw kind в доменное enum-значение."""
        if isinstance(value, cls):
            return value
        return cls(str(value).strip().lower())
