from __future__ import annotations

from enum import StrEnum


class ObjectFeatureStatus(StrEnum):
    """Статус включения feature config runtime-объекта."""

    ENABLED = "enabled"
    DISABLED = "disabled"

    @classmethod
    def from_value(
        cls,
        value: str | "ObjectFeatureStatus",
    ) -> "ObjectFeatureStatus":
        """Нормализует raw status в доменное enum-значение."""
        if isinstance(value, cls):
            return value
        return cls(str(value).strip().lower())
