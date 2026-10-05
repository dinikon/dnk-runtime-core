from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class IsTenantLocaleSelectedDTO:
    """Результат проверки выбранной локали."""

    selected: bool
