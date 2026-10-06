from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class PutVariantContentResultDTO:
    variant_id: UUID
    locale: str
    schema_version: int
    blocks: dict[str, str]
