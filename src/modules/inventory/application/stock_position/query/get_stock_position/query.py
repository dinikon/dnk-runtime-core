from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class GetStockPositionQuery:
    """Задаёт конкретный сценарий чтения физического учёта."""

    identifier: UUID
