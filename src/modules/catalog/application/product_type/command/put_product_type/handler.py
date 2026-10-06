from src.modules.catalog.application.content_block.port.query_repository import (
    ContentBlockQueryRepositoryProtocol,
)
from src.modules.catalog.application.product_type.validate_translations import (
    validate_active_translations,
)
from src.modules.catalog.application.product_type.command.put_product_type.command import (
    PutProductTypeCommand,
)
from src.modules.catalog.application.product_type.command.put_product_type.dto import (
    PutProductTypeResultDTO,
)
from src.modules.catalog.application.product_type.port.locale_reader import (
    ProductTypeLocaleReaderPort,
)
from src.modules.catalog.application.product_type.port.usage_reader import (
    ProductTypeUsageReaderPort,
)
from src.modules.catalog.application.product_type.resolve_blocks import resolve_blocks
from src.modules.catalog.domain.product_type.error import (
    ProductTypeConflictError,
    ProductTypeNotFoundError,
)
from src.modules.catalog.domain.product_type.repository import (
    ProductTypeRepositoryProtocol,
)


class PutProductTypeHandler:
    def __init__(
        self,
        repository: ProductTypeRepositoryProtocol,
        definitions: ContentBlockQueryRepositoryProtocol,
        usage: ProductTypeUsageReaderPort,
        locales: ProductTypeLocaleReaderPort,
    ) -> None:
        self._repository, self._definitions = repository, definitions
        self._usage, self._locales = usage, locales

    async def execute(self, command: PutProductTypeCommand) -> PutProductTypeResultDTO:
        await validate_active_translations(command.translations, self._locales)
        product_type = await self._repository.get_for_update(command.type_id)
        if product_type is None:
            raise ProductTypeNotFoundError("Product type not found.")
        if product_type.schema_version != command.expected_schema_version:
            raise ProductTypeConflictError("Product type schema version changed.")
        product_type.validate_blocks(command.blocks)
        resolved = await resolve_blocks(command.blocks, self._definitions)
        old = {(item.scope, item.block_id): item for item in product_type.blocks}
        new = {(item.scope, item.block_id): item for item in command.blocks}
        if product_type.is_system and set(old.values()) != set(new.values()):
            raise ProductTypeConflictError(
                "System product type structure cannot be changed."
            )
        for key, item in old.items():
            if key not in new and await self._usage.content_block_in_use(
                command.type_id, item.scope, item.block_id
            ):
                raise ProductTypeConflictError(
                    "Cannot remove a block with saved values."
                )
        for key, item in new.items():
            if item.required and (key not in old or not old[key].required):
                if await self._usage.missing_required_value(
                    command.type_id, item.scope, item.block_id
                ):
                    raise ProductTypeConflictError(
                        "Existing content lacks the required block."
                    )
        product_type.replace_translations(command.translations)
        product_type.replace_blocks(command.blocks)
        await self._repository.save(product_type)
        return PutProductTypeResultDTO(
            product_type.id.uuid,
            product_type.code,
            product_type.is_system,
            product_type.schema_version,
            dict(product_type.translations),
            resolved,
        )
