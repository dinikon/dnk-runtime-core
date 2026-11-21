from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class GetPackagingTypeResultDTO:
    """Передаёт конкретную проекцию карточки без восстановления Domain."""

    id: UUID
    code: str
    name: str
    is_active: bool
