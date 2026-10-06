from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class PutVariantContentResultDTO:
    variant_id: UUID
    locale: str
    short_description: str
