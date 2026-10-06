from uuid import UUID

from src.modules.catalog.application.content_schema.contracts import (
    BlockDefinitionDTO,
    ContentSchemaRepositoryProtocol,
    ProductTypeSchemaDTO,
    SchemaBlockDTO,
)
from src.modules.catalog.application.product.port.locale_reader import LocaleReaderPort
from src.modules.catalog.domain.content_block.aggregate import ContentBlockDefinition
from src.modules.catalog.domain.content_block.value_object.content_block import (
    ContentBlockCodeVO,
    ContentBlockIdVO,
    ContentBlockTranslationVO,
    ContentBlockType,
)
from src.modules.catalog.domain.product_type.aggregate import (
    ContentScope,
    ProductType,
    ProductTypeContentBlock,
)
from src.modules.catalog.domain.product_type.value_object.product_type_id import (
    ProductTypeIdVO,
)
from src.modules.shared.application.uuid.uuid_port import UUIdGeneratorProtocol


class SchemaNotFoundError(Exception):
    pass


class SchemaConflictError(Exception):
    pass


class SchemaValidationError(Exception):
    pass


class ContentSchemaService:
    """Сценарии определения блоков и шаблонов без управления транзакцией."""

    def __init__(
        self,
        repository: ContentSchemaRepositoryProtocol,
        locales: LocaleReaderPort,
        uuids: UUIdGeneratorProtocol,
    ) -> None:
        self._repository = repository
        self._locales = locales
        self._uuids = uuids

    async def list_blocks(self) -> tuple[BlockDefinitionDTO, ...]:
        return await self._repository.list_blocks()

    async def get_block(self, block_id: UUID) -> BlockDefinitionDTO:
        item = await self._repository.get_block(block_id)
        if item is None:
            raise SchemaNotFoundError("Content block not found.")
        return item

    async def list_types(self) -> tuple[ProductTypeSchemaDTO, ...]:
        return await self._repository.list_types()

    async def get_type(self, type_id: UUID) -> ProductTypeSchemaDTO:
        item = await self._repository.get_type(type_id)
        if item is None:
            raise SchemaNotFoundError("Product type not found.")
        return item

    async def _validate_translations(self, translations: dict[str, str]) -> None:
        if not translations:
            raise SchemaValidationError("At least one translation is required.")
        for locale in translations:
            if not await self._locales.is_active(locale):
                raise SchemaValidationError("Locale is not active.")

    async def create_block(
        self, code: str, type: ContentBlockType, translations: dict[str, str]
    ) -> BlockDefinitionDTO:
        await self._validate_translations(translations)
        try:
            block = ContentBlockDefinition.create(
                id=ContentBlockIdVO.from_value(self._uuids.new()),
                code=ContentBlockCodeVO(code),
                type=type,
                translations={
                    locale: ContentBlockTranslationVO(name)
                    for locale, name in translations.items()
                },
            )
        except ValueError as exc:
            raise SchemaValidationError(str(exc)) from exc
        result = BlockDefinitionDTO(
            block.id.uuid,
            block.code.value,
            block.type,
            False,
            {k: v.name for k, v in block.translations.items()},
        )
        await self._repository.add_block(result)
        return result

    async def update_block(
        self, block_id: UUID, type: ContentBlockType, translations: dict[str, str]
    ) -> BlockDefinitionDTO:
        await self._validate_translations(translations)
        block = await self._repository.get_block(block_id)
        if block is None:
            raise SchemaNotFoundError("Content block not found.")
        if block.is_system and type != block.type:
            raise SchemaConflictError("System content block type cannot be changed.")
        if type != block.type and await self._repository.block_in_use(block_id):
            raise SchemaConflictError("Used content block type cannot be changed.")
        try:
            definition = ContentBlockDefinition.create(
                id=ContentBlockIdVO.from_value(block.id),
                code=ContentBlockCodeVO(block.code),
                type=block.type,
                is_system=block.is_system,
                translations={
                    locale: ContentBlockTranslationVO(name)
                    for locale, name in block.translations.items()
                },
            )
            if type != definition.type:
                definition.change_type(type)
            definition.replace_translations(
                {
                    locale: ContentBlockTranslationVO(name)
                    for locale, name in translations.items()
                }
            )
        except ValueError as exc:
            raise SchemaValidationError(str(exc)) from exc
        result = BlockDefinitionDTO(
            definition.id.uuid,
            definition.code.value,
            definition.type,
            definition.is_system,
            {locale: item.name for locale, item in definition.translations.items()},
        )
        await self._repository.update_block(result)
        return result

    async def delete_block(self, block_id: UUID) -> None:
        block = await self._repository.get_block(block_id)
        if block is None:
            raise SchemaNotFoundError("Content block not found.")
        if block.is_system or await self._repository.block_in_use(block_id):
            raise SchemaConflictError("Content block is system or in use.")
        await self._repository.delete_block(block_id)

    async def create_type(
        self,
        code: str,
        translations: dict[str, str],
        blocks: tuple[ProductTypeContentBlock, ...],
    ) -> ProductTypeSchemaDTO:
        await self._validate_translations(translations)
        try:
            product_type = ProductType.create(
                id=ProductTypeIdVO.from_value(self._uuids.new()),
                code=code,
                translations=translations,
                blocks=blocks,
            )
        except ValueError as exc:
            raise SchemaValidationError(str(exc)) from exc
        resolved = await self._resolve_blocks(blocks)
        result = ProductTypeSchemaDTO(
            product_type.id.uuid,
            product_type.code,
            False,
            1,
            dict(product_type.translations),
            resolved,
        )
        await self._repository.add_type(result)
        return result

    async def update_type(
        self,
        type_id: UUID,
        translations: dict[str, str],
        blocks: tuple[ProductTypeContentBlock, ...],
        expected_version: int,
    ) -> ProductTypeSchemaDTO:
        await self._validate_translations(translations)
        current = await self._repository.get_type(type_id, lock=True)
        if current is None:
            raise SchemaNotFoundError("Product type not found.")
        if current.schema_version != expected_version:
            raise SchemaConflictError("Product type schema version changed.")
        try:
            ProductType._check_blocks(blocks)
        except ValueError as exc:
            raise SchemaValidationError(str(exc)) from exc
        resolved = await self._resolve_blocks(blocks)
        old_assignments = {
            (item.scope, item.block_id, item.required, item.position)
            for item in current.blocks
        }
        new_assignments = {
            (item.scope, item.block_id, item.required, item.position)
            for item in resolved
        }
        if current.is_system and old_assignments != new_assignments:
            raise SchemaConflictError(
                "System product type structure cannot be changed."
            )
        old = {(item.scope, item.block_id): item for item in current.blocks}
        new = {(item.scope, item.block_id): item for item in resolved}
        for key, item in old.items():
            if key not in new and await self._repository.content_block_in_use(
                type_id, item.scope, item.block_id
            ):
                raise SchemaConflictError("Cannot remove a block with saved values.")
        for key, item in new.items():
            if item.required and (key not in old or not old[key].required):
                if await self._repository.missing_required_value(
                    type_id, item.scope, item.block_id
                ):
                    raise SchemaConflictError(
                        "Existing content lacks the required block."
                    )
        try:
            product_type = ProductType.restore(
                id=ProductTypeIdVO.from_value(current.id),
                code=current.code,
                is_system=current.is_system,
                schema_version=current.schema_version,
                translations=current.translations,
                blocks=tuple(
                    ProductTypeContentBlock(
                        ContentBlockIdVO.from_value(item.block_id),
                        item.scope,
                        item.required,
                        item.position,
                    )
                    for item in current.blocks
                ),
            )
            product_type.replace_translations(translations)
            if old_assignments != new_assignments:
                product_type.replace_blocks(blocks)
        except ValueError as exc:
            raise SchemaValidationError(str(exc)) from exc
        result = ProductTypeSchemaDTO(
            current.id,
            current.code,
            current.is_system,
            product_type.schema_version,
            dict(product_type.translations),
            resolved,
        )
        await self._repository.update_type(result)
        return result

    async def _resolve_blocks(
        self, blocks: tuple[ProductTypeContentBlock, ...]
    ) -> tuple[SchemaBlockDTO, ...]:
        resolved = []
        for item in blocks:
            definition = await self._repository.get_block(item.block_id.uuid)
            if definition is None:
                raise SchemaNotFoundError("Content block not found.")
            resolved.append(
                SchemaBlockDTO(
                    definition.id,
                    definition.code,
                    definition.type,
                    item.scope,
                    item.required,
                    item.position,
                    definition.translations,
                )
            )
        return tuple(
            sorted(resolved, key=lambda item: (item.scope.value, item.position))
        )

    async def delete_type(self, type_id: UUID) -> None:
        item = await self._repository.get_type(type_id, lock=True)
        if item is None:
            raise SchemaNotFoundError("Product type not found.")
        if item.is_system or await self._repository.type_in_use(type_id):
            raise SchemaConflictError("Product type is system or in use.")
        await self._repository.delete_type(type_id)
