from src.modules.catalog.application.content_block.port.query_repository import (
    ContentBlockQueryRepositoryProtocol,
)
from src.modules.catalog.application.product_type.validate_translations import (
    validate_active_translations,
)
from src.modules.catalog.application.product_type.command.create_product_type.command import (
    CreateProductTypeCommand,
)
from src.modules.catalog.application.product_type.command.create_product_type.dto import (
    CreateProductTypeResultDTO,
)
from src.modules.catalog.application.product_type.port.locale_reader import (
    ProductTypeLocaleReaderPort,
)
from src.modules.catalog.application.product_type.resolve_blocks import resolve_blocks
from src.modules.catalog.domain.product_type.aggregate import ProductType
from src.modules.catalog.domain.product_type.repository import (
    ProductTypeRepositoryProtocol,
)
from src.modules.catalog.domain.product_type.value_object.product_type_id import (
    ProductTypeIdVO,
)
from src.modules.shared.application.uuid.uuid_port import UUIdGeneratorProtocol


class CreateProductTypeHandler:
    def __init__(
        self,
        repository: ProductTypeRepositoryProtocol,
        definitions: ContentBlockQueryRepositoryProtocol,
        locales: ProductTypeLocaleReaderPort,
        uuids: UUIdGeneratorProtocol,
    ) -> None:
        self._repository, self._definitions, self._locales, self._uuids = (
            repository,
            definitions,
            locales,
            uuids,
        )

    async def execute(
        self, command: CreateProductTypeCommand
    ) -> CreateProductTypeResultDTO:
        await validate_active_translations(command.translations, self._locales)
        product_type = ProductType.create(
            id=ProductTypeIdVO.from_value(self._uuids.new()),
            code=command.code,
            translations=command.translations,
            blocks=command.blocks,
        )
        resolved = await resolve_blocks(product_type.blocks, self._definitions)
        await self._repository.add(product_type)
        return CreateProductTypeResultDTO(
            product_type.id.uuid,
            product_type.code,
            product_type.is_system,
            product_type.schema_version,
            dict(product_type.translations),
            resolved,
        )
