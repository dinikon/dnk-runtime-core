from __future__ import annotations

from enum import StrEnum


class ObjectFeatureCode(StrEnum):
    """Строгий справочник поддержанных object feature codes."""

    CONTACT_POINT = "CONTACT_POINT"

    @classmethod
    def from_value(
        cls,
        value: str | "ObjectFeatureCode",
    ) -> "ObjectFeatureCode":
        """Нормализует raw feature code в enum-значение справочника."""
        if isinstance(value, cls):
            return value
        return cls(str(value).strip().upper())
