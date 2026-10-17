from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class ContactPointDraftDTO:
    value: str
    binding_id: UUID | None = None
    label_id: UUID | None = None
    country_code: str | None = None


@dataclass(frozen=True, slots=True)
class ContactPointDTO:
    binding_id: UUID
    contact_point_id: UUID
    type: str
    value: str
    country_code: str | None
    label_id: UUID | None
    position: int


@dataclass(frozen=True, slots=True)
class ContactPointsDTO:
    phones: tuple[ContactPointDTO, ...]
    emails: tuple[ContactPointDTO, ...]
