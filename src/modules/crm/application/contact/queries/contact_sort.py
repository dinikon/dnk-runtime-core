from dataclasses import dataclass
from typing import Literal

ContactSortField = Literal[
    "created_at",
    "updated_at",
    "first_name",
    "last_name",
    "middle_name",
]


@dataclass(frozen=True, slots=True)
class ContactSort:
    field: ContactSortField = "created_at"
    direction: Literal["asc", "desc"] = "desc"
