from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class ReturnDestinationDTO:
    """Передаёт подпись допустимой локации назначения."""

    id: UUID
    code: str
    name: str


@dataclass(frozen=True, slots=True)
class ListReturnDestinationsResultDTO:
    """Передаёт страницу локаций без восстановления Domain."""

    items: tuple[ReturnDestinationDTO, ...]
    total: int
    offset: int
    limit: int
