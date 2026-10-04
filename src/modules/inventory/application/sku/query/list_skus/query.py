from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ListSkusQuery:
    """Ограниченная страница SKU с устойчивым порядком code, id."""

    limit: int = 50
    offset: int = 0
