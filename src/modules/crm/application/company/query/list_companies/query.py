from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ListCompaniesQuery:
    """Все компании текущего tenant без фильтрации и пагинации."""
