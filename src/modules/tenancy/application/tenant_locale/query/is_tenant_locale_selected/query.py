from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class IsTenantLocaleSelectedQuery:
    """Проверка локали для будущих сценариев Catalog и Channels."""

    code: str
