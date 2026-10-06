from dataclasses import dataclass
from uuid import UUID

from src.modules.catalog.application.product_type.port.schema_reader import (
    SchemaBlockDTO,
)


@dataclass(frozen=True, slots=True)
class PutProductTypeResultDTO:
    id: UUID
    code: str
    is_system: bool
    schema_version: int
    translations: dict[str, str]
    blocks: tuple[SchemaBlockDTO, ...]
