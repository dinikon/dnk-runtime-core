from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ValidateCurrencyResultDTO:
    """Публичные сведения об одной проверенной активной валюте."""

    code: str
    numeric_code: str | None
    minor_units: int | None
