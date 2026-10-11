from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ValidateCurrencyQuery:
    """Запрашивает проверку кода в активном справочнике валют."""

    code: str
