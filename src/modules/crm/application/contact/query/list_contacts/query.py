from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ListContactsQuery:
    """Все контакты tenant без фильтрации и пагинации."""
