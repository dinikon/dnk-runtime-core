from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class AttributeOptionDTO:
    id: UUID
    code: str
    name: str | None


@dataclass(frozen=True, slots=True)
class AttributeDetailsDTO:
    id: UUID
    code: str
    type: str
    name: str | None
    options: tuple[AttributeOptionDTO, ...]
