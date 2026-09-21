from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ListCurrenciesQuery:
    """Input for list currencies."""

    pass


__all__ = ["ListCurrenciesQuery"]
