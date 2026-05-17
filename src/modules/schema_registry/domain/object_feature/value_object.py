from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import re

from src.modules.schema_registry.domain.error import InvalidValueObjectError
from src.modules.shared import EntityIdVO

_FEATURE_CODE_RE = re.compile(r"^[A-Z][A-Z0-9_]*$")


class ObjectFeatureConfigIdVO(EntityIdVO):
    """Value object идентификатора object feature config metadata."""


class ObjectFeatureCode(StrEnum):
    """Строгий справочник поддержанных object feature codes."""

    CONTACT_POINTS = "CONTACT_POINTS"
    INVENTORY = "INVENTORY"

    @classmethod
    def from_value(
        cls,
        value: str | "ObjectFeatureCode",
    ) -> "ObjectFeatureCode":
        """Нормализует raw feature code в enum-значение справочника."""
        if isinstance(value, cls):
            return value
        return cls(str(value).strip().upper())


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
