from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class ChangeProductKindResultDTO:
    """Собственный результат сценария change_product_kind."""

    id: UUID
    revision: int
