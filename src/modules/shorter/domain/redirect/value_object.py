from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlparse

from src.modules.shared import EntityIdVO
from src.modules.shorter.domain.errors import RedirectTargetUrlInvalidError

UTM_PARAMETER_NAMES = (
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_id",
    "utm_term",
    "utm_content",
)


class RedirectIdVO(EntityIdVO): ...


@dataclass(frozen=True, slots=True)
class RedirectTargetUrlVO:
    value: str

    def __post_init__(self) -> None:
        normalized = self.value.strip()
        parsed = urlparse(normalized)
        if parsed.scheme != "https" or not parsed.netloc:
            raise RedirectTargetUrlInvalidError(target_url=normalized)
        object.__setattr__(self, "value", normalized)


@dataclass(frozen=True, slots=True)
class RedirectUtmParametersVO:
    utm_source: str | None = None
    utm_medium: str | None = None
    utm_campaign: str | None = None
    utm_id: str | None = None
    utm_term: str | None = None
    utm_content: str | None = None

    def __post_init__(self) -> None:
        for field_name in UTM_PARAMETER_NAMES:
            raw_value = getattr(self, field_name)
            normalized_value = self._normalize_value(raw_value)
            object.__setattr__(self, field_name, normalized_value)

    @classmethod
    def from_mapping(
        cls,
        values: dict[str, object] | None,
    ) -> "RedirectUtmParametersVO":
        if not values:
            return cls()
        return cls(
            utm_source=cls._normalize_value(values.get("utm_source")),
            utm_medium=cls._normalize_value(values.get("utm_medium")),
            utm_campaign=cls._normalize_value(values.get("utm_campaign")),
            utm_id=cls._normalize_value(values.get("utm_id")),
            utm_term=cls._normalize_value(values.get("utm_term")),
            utm_content=cls._normalize_value(values.get("utm_content")),
        )

    def as_dict(self) -> dict[str, str]:
        payload: dict[str, str] = {}
        for field_name in UTM_PARAMETER_NAMES:
            value = getattr(self, field_name)
            if value is not None:
                payload[field_name] = value
        return payload

    @staticmethod
    def _normalize_value(value: object) -> str | None:
        if value is None:
            return None
        normalized = str(value).strip()
        return normalized or None


__all__ = [
    "RedirectIdVO",
    "RedirectTargetUrlVO",
    "RedirectUtmParametersVO",
    "UTM_PARAMETER_NAMES",
]
