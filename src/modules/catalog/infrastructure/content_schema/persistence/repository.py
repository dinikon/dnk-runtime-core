from typing import Any, cast
from uuid import UUID

from sqlalchemy import delete, exists, insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.engine import CursorResult

from src.modules.catalog.application.content_schema.contracts import (
    BlockDefinitionDTO,
    ProductTypeSchemaDTO,
    SchemaBlockDTO,
)
from src.modules.catalog.domain.content_block.value_object.content_block import (
    ContentBlockType,
)
from src.modules.catalog.domain.product_type.aggregate import ContentScope
from src.modules.catalog.infrastructure.persistence.models.content_block import (
    ContentBlockDefinitionModel,
    ContentBlockTranslationModel,
)
from src.modules.catalog.infrastructure.persistence.models.content_value import (
    ProductContentValueModel,
    VariantContentValueModel,
)
from src.modules.catalog.infrastructure.persistence.models.content import (
    ProductContentModel,
)
from src.modules.catalog.infrastructure.persistence.models.variant_content import (
    VariantContentModel,
)
from src.modules.catalog.infrastructure.persistence.models.product import ProductModel
from src.modules.catalog.infrastructure.persistence.models.variant import VariantModel
from src.modules.catalog.infrastructure.persistence.models.product_type import (
    ProductTypeContentBlockModel,
    ProductTypeModel,
    ProductTypeTranslationModel,
)


class SqlAlchemyContentSchemaRepository:
    """Схемы контента в общей tenant-сессии; транзакцией владеет UoW."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_block(self, block_id: UUID) -> BlockDefinitionDTO | None:
        row = await self._session.get(ContentBlockDefinitionModel, block_id)
        if row is None:
            return None
        translations = (
            (
                await self._session.execute(
                    select(ContentBlockTranslationModel).where(
                        ContentBlockTranslationModel.block_id == block_id
                    )
                )
            )
            .scalars()
            .all()
        )
        return BlockDefinitionDTO(
            row.id,
            row.code,
            ContentBlockType(row.type),
            row.is_system,
            {item.locale_code: item.name for item in translations},
        )

    async def list_blocks(self) -> tuple[BlockDefinitionDTO, ...]:
        rows = (
            await self._session.execute(
                select(ContentBlockDefinitionModel, ContentBlockTranslationModel)
                .outerjoin(
                    ContentBlockTranslationModel,
                    ContentBlockTranslationModel.block_id
                    == ContentBlockDefinitionModel.id,
                )
                .order_by(
                    ContentBlockDefinitionModel.code,
                    ContentBlockTranslationModel.locale_code,
                )
            )
        ).all()
        blocks: dict[UUID, BlockDefinitionDTO] = {}
        for definition, translation in rows:
            block = blocks.get(definition.id)
            if block is None:
                block = BlockDefinitionDTO(
                    definition.id,
                    definition.code,
                    ContentBlockType(definition.type),
                    definition.is_system,
                    {},
                )
                blocks[definition.id] = block
            if translation is not None:
                block.translations[translation.locale_code] = translation.name
        return tuple(blocks.values())

    async def add_block(self, block: BlockDefinitionDTO) -> None:
        await self._session.execute(
            insert(ContentBlockDefinitionModel).values(
                id=block.id,
                code=block.code,
                type=block.type.value,
                is_system=block.is_system,
            )
        )
        await self._write_block_translations(block)

    async def update_block(self, block: BlockDefinitionDTO) -> None:
        await self._session.execute(
            update(ContentBlockDefinitionModel)
            .where(ContentBlockDefinitionModel.id == block.id)
            .values(type=block.type.value)
        )
        await self._session.execute(
            delete(ContentBlockTranslationModel).where(
                ContentBlockTranslationModel.block_id == block.id
            )
        )
        await self._write_block_translations(block)

    async def _write_block_translations(self, block: BlockDefinitionDTO) -> None:
        if block.translations:
            await self._session.execute(
                insert(ContentBlockTranslationModel),
                [
                    {"block_id": block.id, "locale_code": locale, "name": name}
                    for locale, name in block.translations.items()
                ],
            )

    async def delete_block(self, block_id: UUID) -> bool:
        result = cast(
            CursorResult[Any],
            await self._session.execute(
                delete(ContentBlockDefinitionModel).where(
                    ContentBlockDefinitionModel.id == block_id
                )
            ),
        )
        return bool(result.rowcount)

    async def block_in_use(self, block_id: UUID) -> bool:
        for model in (
            ProductTypeContentBlockModel,
            ProductContentValueModel,
            VariantContentValueModel,
        ):
            if await self._session.scalar(
                select(exists().where(model.block_id == block_id))
            ):
                return True
        return False

    async def get_type(
        self, type_id: UUID, *, lock: bool = False
    ) -> ProductTypeSchemaDTO | None:
        statement = select(ProductTypeModel).where(ProductTypeModel.id == type_id)
        if lock:
            statement = statement.with_for_update()
        row = (await self._session.execute(statement)).scalar_one_or_none()
        if row is None:
            return None
        names = (
            (
                await self._session.execute(
                    select(ProductTypeTranslationModel).where(
                        ProductTypeTranslationModel.product_type_id == type_id
                    )
                )
            )
            .scalars()
            .all()
        )
        assignments = (
            (
                await self._session.execute(
                    select(ProductTypeContentBlockModel)
                    .where(ProductTypeContentBlockModel.product_type_id == type_id)
                    .order_by(
                        ProductTypeContentBlockModel.scope,
                        ProductTypeContentBlockModel.position,
                    )
                )
            )
            .scalars()
            .all()
        )
        definitions = {item.id: item for item in await self.list_blocks()}
        return ProductTypeSchemaDTO(
            id=row.id,
            code=row.code,
            is_system=row.is_system,
            schema_version=row.schema_version,
            translations={item.locale_code: item.name for item in names},
            blocks=tuple(
                SchemaBlockDTO(
                    item.block_id,
                    definitions[item.block_id].code,
                    definitions[item.block_id].type,
                    ContentScope(item.scope),
                    item.required,
                    item.position,
                    definitions[item.block_id].translations,
                )
                for item in assignments
            ),
        )

    async def get_clean_type(self) -> ProductTypeSchemaDTO:
        type_id = await self._session.scalar(
            select(ProductTypeModel.id).where(ProductTypeModel.code == "clean")
        )
        if type_id is None:
            raise RuntimeError("Clean product type seed is missing.")
        result = await self.get_type(type_id)
        if result is None:
            raise RuntimeError("Clean product type seed is missing.")
        return result

    async def list_types(self) -> tuple[ProductTypeSchemaDTO, ...]:
        ids = (
            (
                await self._session.execute(
                    select(ProductTypeModel.id).order_by(ProductTypeModel.code)
                )
            )
            .scalars()
            .all()
        )
        return tuple([await self.get_type(item) for item in ids])  # type: ignore[misc]

    async def add_type(self, item: ProductTypeSchemaDTO) -> None:
        await self._session.execute(
            insert(ProductTypeModel).values(
                id=item.id,
                code=item.code,
                is_system=item.is_system,
                schema_version=item.schema_version,
            )
        )
        await self._write_type_children(item)

    async def update_type(self, item: ProductTypeSchemaDTO) -> None:
        await self._session.execute(
            update(ProductTypeModel)
            .where(ProductTypeModel.id == item.id)
            .values(schema_version=item.schema_version)
        )
        await self._session.execute(
            delete(ProductTypeContentBlockModel).where(
                ProductTypeContentBlockModel.product_type_id == item.id
            )
        )
        await self._session.execute(
            delete(ProductTypeTranslationModel).where(
                ProductTypeTranslationModel.product_type_id == item.id
            )
        )
        await self._write_type_children(item)

    async def _write_type_children(self, item: ProductTypeSchemaDTO) -> None:
        await self._session.execute(
            insert(ProductTypeTranslationModel),
            [
                {"product_type_id": item.id, "locale_code": locale, "name": name}
                for locale, name in item.translations.items()
            ],
        )
        if item.blocks:
            await self._session.execute(
                insert(ProductTypeContentBlockModel),
                [
                    {
                        "product_type_id": item.id,
                        "scope": block.scope.value,
                        "block_id": block.block_id,
                        "required": block.required,
                        "position": block.position,
                    }
                    for block in item.blocks
                ],
            )

    async def delete_type(self, type_id: UUID) -> bool:
        result = cast(
            CursorResult[Any],
            await self._session.execute(
                delete(ProductTypeModel).where(ProductTypeModel.id == type_id)
            ),
        )
        return bool(result.rowcount)

    async def type_in_use(self, type_id: UUID) -> bool:
        return bool(
            await self._session.scalar(
                select(exists().where(ProductModel.product_type_id == type_id))
            )
        )

    async def content_block_in_use(
        self, type_id: UUID, scope: ContentScope, block_id: UUID
    ) -> bool:
        if scope is ContentScope.PRODUCT:
            stmt = select(
                exists()
                .select_from(ProductContentValueModel)
                .join(
                    ProductModel, ProductModel.id == ProductContentValueModel.product_id
                )
                .where(
                    ProductModel.product_type_id == type_id,
                    ProductContentValueModel.block_id == block_id,
                )
            )
        else:
            stmt = select(
                exists()
                .select_from(VariantContentValueModel)
                .join(
                    VariantModel, VariantModel.id == VariantContentValueModel.variant_id
                )
                .join(ProductModel, ProductModel.id == VariantModel.product_id)
                .where(
                    ProductModel.product_type_id == type_id,
                    VariantContentValueModel.block_id == block_id,
                )
            )
        return bool(await self._session.scalar(stmt))

    async def missing_required_value(
        self, type_id: UUID, scope: ContentScope, block_id: UUID
    ) -> bool:
        if scope is ContentScope.PRODUCT:
            stmt = (
                select(ProductContentModel.product_id)
                .join(ProductModel, ProductModel.id == ProductContentModel.product_id)
                .where(
                    ProductModel.product_type_id == type_id,
                    ~exists().where(
                        ProductContentValueModel.product_id
                        == ProductContentModel.product_id,
                        ProductContentValueModel.locale_code
                        == ProductContentModel.locale_code,
                        ProductContentValueModel.block_id == block_id,
                    ),
                )
                .limit(1)
            )
        else:
            stmt = (
                select(VariantContentModel.variant_id)
                .join(VariantModel, VariantModel.id == VariantContentModel.variant_id)
                .join(ProductModel, ProductModel.id == VariantModel.product_id)
                .where(
                    ProductModel.product_type_id == type_id,
                    ~exists().where(
                        VariantContentValueModel.variant_id
                        == VariantContentModel.variant_id,
                        VariantContentValueModel.locale_code
                        == VariantContentModel.locale_code,
                        VariantContentValueModel.block_id == block_id,
                    ),
                )
                .limit(1)
            )
        return (await self._session.scalar(stmt)) is not None
