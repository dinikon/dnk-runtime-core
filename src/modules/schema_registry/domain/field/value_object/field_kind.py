from __future__ import annotations

from enum import StrEnum


class FieldKind(StrEnum):
    """Классификация поля runtime-объекта по происхождению и поведению."""

    CUSTOM = "custom"
    STANDARD = "standard"
    SYSTEM = "system"

    @classmethod
    def from_value(cls, value: str | "FieldKind") -> "FieldKind":
        """Нормализует raw kind в доменное enum-значение."""
        if isinstance(value, cls):
            return value
        return cls(str(value).strip().lower())
