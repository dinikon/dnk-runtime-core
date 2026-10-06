from src.modules.catalog.application.content_block.port.query_repository import (
    ContentBlockQueryRepositoryProtocol,
)
from src.modules.catalog.application.product_type.port.schema_reader import (
    SchemaBlockDTO,
)
from src.modules.catalog.domain.content_block.error import ContentBlockNotFoundError
from src.modules.catalog.domain.product_type.aggregate import ProductTypeContentBlock


async def resolve_blocks(
    blocks: tuple[ProductTypeContentBlock, ...],
    definitions: ContentBlockQueryRepositoryProtocol,
) -> tuple[SchemaBlockDTO, ...]:
    """Дополняет ссылки ProductType данными определений для чтения схемы."""
    result = []
    for assignment in blocks:
        definition = await definitions.get(assignment.block_id)
        if definition is None:
            raise ContentBlockNotFoundError("Content block not found.")
        result.append(
            SchemaBlockDTO(
                definition.id,
                definition.code,
                definition.type,
                assignment.scope,
                assignment.required,
                assignment.position,
                definition.translations,
            )
        )
    return tuple(sorted(result, key=lambda item: (item.scope.value, item.position)))
