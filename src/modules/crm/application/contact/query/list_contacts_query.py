from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class ListContactsQuery:
    limit: int
    offset: int
