from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ListSkusQuery:
    """Ограниченная страница SKU с устойчивым порядком code, id."""

    limit: int = 50
    offset: int = 0

    def __post_init__(self) -> None:
        if type(self.limit) is not int or not 1 <= self.limit <= 200:
            raise ValueError("limit must be between 1 and 200.")
        if type(self.offset) is not int or self.offset < 0:
            raise ValueError("offset must be a non-negative integer.")
