from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class UpdatePackagingTypeResultDTO:
    """Передаёт полную карточку после изменения параметров типа тары."""

    id: UUID
    code: str
    name: str
    is_active: bool
