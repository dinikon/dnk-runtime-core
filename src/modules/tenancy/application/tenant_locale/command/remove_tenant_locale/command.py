from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RemoveTenantLocaleCommand:
    """Исключение локали из набора текущего tenant."""

    code: str
