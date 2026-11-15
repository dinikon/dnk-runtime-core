from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class GetStockPostingQuery:
    """Передаёт идентификатор факта внутри текущего tenant."""

    identifier: UUID
