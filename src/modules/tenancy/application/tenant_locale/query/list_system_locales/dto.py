from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SystemLocaleDTO:
    """Доступная для выбора локаль."""

    code: str
    name: str
