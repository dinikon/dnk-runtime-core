from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from src.modules.catalog.domain.content_block.value_object.content_block import (
    ContentBlockType,
)
from src.modules.catalog.domain.product_type.aggregate import ContentScope


@dataclass(frozen=True, slots=True)
class BlockDefinitionDTO:
    id: UUID
    code: str
    type: ContentBlockType
    is_system: bool
    translations: dict[str, str]


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


class ContentSchemaRepositoryProtocol(Protocol):
    async def get_type(
        self, type_id: UUID, *, lock: bool = False
    ) -> ProductTypeSchemaDTO | None: ...
    async def get_clean_type(self) -> ProductTypeSchemaDTO: ...
    async def list_types(self) -> tuple[ProductTypeSchemaDTO, ...]: ...
    async def get_block(self, block_id: UUID) -> BlockDefinitionDTO | None: ...
    async def list_blocks(self) -> tuple[BlockDefinitionDTO, ...]: ...
    async def add_block(self, block: BlockDefinitionDTO) -> None: ...
    async def update_block(self, block: BlockDefinitionDTO) -> None: ...
    async def delete_block(self, block_id: UUID) -> bool: ...
    async def block_in_use(self, block_id: UUID) -> bool: ...
    async def add_type(self, product_type: ProductTypeSchemaDTO) -> None: ...
    async def update_type(self, product_type: ProductTypeSchemaDTO) -> None: ...
    async def delete_type(self, type_id: UUID) -> bool: ...
    async def type_in_use(self, type_id: UUID) -> bool: ...
    async def content_block_in_use(
        self, type_id: UUID, scope: ContentScope, block_id: UUID
    ) -> bool: ...
    async def missing_required_value(
        self, type_id: UUID, scope: ContentScope, block_id: UUID
    ) -> bool: ...
