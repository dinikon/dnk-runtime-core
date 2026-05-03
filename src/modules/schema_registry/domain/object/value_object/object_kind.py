from __future__ import annotations

from enum import StrEnum


class ObjectKind(StrEnum):
    """Классификация runtime-объекта по происхождению и поведению."""

    CUSTOM = "custom"
    STANDARD = "standard"
    SYSTEM = "system"
    VIEW = "view"

    @classmethod
    def from_value(cls, value: str | "ObjectKind") -> "ObjectKind":
        """Нормализует raw kind в доменное enum-значение."""
        if isinstance(value, cls):
            return value
        return cls(str(value).strip().lower())
