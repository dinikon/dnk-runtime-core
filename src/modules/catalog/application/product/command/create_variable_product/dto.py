from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class CreateVariableProductResultDTO:
    id: UUID
    variant_ids: tuple[UUID, ...]
