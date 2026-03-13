from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class ContactListFilter:
    ids: tuple[UUID, ...] = ()
    first_name: str | None = None
    last_name: str | None = None
    middle_name: str | None = None
