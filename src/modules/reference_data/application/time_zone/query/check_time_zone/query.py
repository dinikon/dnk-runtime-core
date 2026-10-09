from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CheckTimeZoneQuery:
    """Параметры публичной проверки одного кода IANA timezone."""

    code: str
