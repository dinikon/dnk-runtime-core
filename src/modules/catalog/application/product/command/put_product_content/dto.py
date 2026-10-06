from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class PutProductContentResultDTO:
    product_id: UUID
    locale: str
    schema_version: int
    blocks: dict[str, str]
    updated_at: datetime
    updated_by: UUID
