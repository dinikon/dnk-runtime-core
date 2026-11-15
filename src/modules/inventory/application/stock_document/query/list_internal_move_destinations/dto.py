from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class InternalMoveDestinationDTO:
    """Передаёт подпись допустимой локации назначения."""

    id: UUID
    code: str
    name: str


@dataclass(frozen=True, slots=True)
class ListInternalMoveDestinationsResultDTO:
    """Передаёт страницу локаций без восстановления Domain."""

    items: tuple[InternalMoveDestinationDTO, ...]
    total: int
    offset: int
    limit: int
