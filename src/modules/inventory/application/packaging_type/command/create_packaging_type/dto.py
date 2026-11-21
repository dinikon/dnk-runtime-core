from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class CreatePackagingTypeResultDTO:
    """Передаёт результат создания типа тары с назначенной Domain активностью."""

    id: UUID
    code: str
    name: str
    is_active: bool
