from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from src.modules.catalog.domain.content_block.value_object.content_block import (
    ContentBlockType,
)
from src.modules.catalog.domain.product_type.aggregate import ContentScope


@dataclass(frozen=True, slots=True)
class SchemaBlockDTO:
    block_id: UUID
    code: str
    type: ContentBlockType
    scope: ContentScope
    required: bool
    position: int
    translations: dict[str, str]


@dataclass(frozen=True, slots=True)
class ProductTypeSchemaDTO:
    id: UUID
    code: str
    is_system: bool
    schema_version: int
    translations: dict[str, str]
    blocks: tuple[SchemaBlockDTO, ...]


class ProductTypeSchemaReaderProtocol(Protocol):
    """Снимок схемы типа для сценариев Product и редактора типа."""

    async def get_type(
        self, type_id: UUID, *, lock: bool = False
    ) -> ProductTypeSchemaDTO | None: ...

    async def get_clean_type(self) -> ProductTypeSchemaDTO: ...

    async def list_types(self) -> tuple[ProductTypeSchemaDTO, ...]: ...
