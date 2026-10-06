from collections import defaultdict
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.catalog.application.product_type.port.schema_reader import (
    ProductTypeSchemaDTO,
    SchemaBlockDTO,
)
from src.modules.catalog.domain.content_block.value_object.content_block import (
    ContentBlockType,
)
from src.modules.catalog.domain.product_type.aggregate import ContentScope
from src.modules.catalog.infrastructure.persistence.models.content_block_definition import (
    ContentBlockDefinitionModel,
)
from src.modules.catalog.infrastructure.persistence.models.content_block_translation import (
    ContentBlockTranslationModel,
)
from src.modules.catalog.infrastructure.persistence.models.product_type_content_block import (
    ProductTypeContentBlockModel,
)
from src.modules.catalog.infrastructure.persistence.models.product_type import (
    ProductTypeModel,
)
from src.modules.catalog.infrastructure.persistence.models.product_type_translation import (
    ProductTypeTranslationModel,
)


class SqlAlchemyProductTypeSchemaReader:
    """Читает готовые схемы типов пакетными проекциями."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_type(
        self, type_id: UUID, *, lock: bool = False
    ) -> ProductTypeSchemaDTO | None:
        statement = select(ProductTypeModel).where(ProductTypeModel.id == type_id)
        if lock:
            statement = statement.with_for_update()
        row = (await self._session.execute(statement)).scalar_one_or_none()
        if row is None:
            return None
        return (await self._assemble([row]))[0]

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
        rows = (
            (
                await self._session.execute(
                    select(ProductTypeModel).order_by(ProductTypeModel.code)
                )
            )
            .scalars()
            .all()
        )
        return await self._assemble(list(rows))

    async def _assemble(
        self, types: list[ProductTypeModel]
    ) -> tuple[ProductTypeSchemaDTO, ...]:
        if not types:
            return ()
        type_ids = [item.id for item in types]
        names = (
            (
                await self._session.execute(
                    select(ProductTypeTranslationModel).where(
                        ProductTypeTranslationModel.product_type_id.in_(type_ids)
                    )
                )
            )
            .scalars()
            .all()
        )
        assignments = (
            await self._session.execute(
                select(ProductTypeContentBlockModel, ContentBlockDefinitionModel)
                .join(
                    ContentBlockDefinitionModel,
                    ContentBlockDefinitionModel.id
                    == ProductTypeContentBlockModel.block_id,
                )
                .where(ProductTypeContentBlockModel.product_type_id.in_(type_ids))
                .order_by(
                    ProductTypeContentBlockModel.product_type_id,
                    ProductTypeContentBlockModel.scope,
                    ProductTypeContentBlockModel.position,
                )
            )
        ).all()
        block_ids = {definition.id for _, definition in assignments}
        block_translations = (
            (
                await self._session.execute(
                    select(ContentBlockTranslationModel).where(
                        ContentBlockTranslationModel.block_id.in_(block_ids)
                    )
                )
            )
            .scalars()
            .all()
            if block_ids
            else []
        )
        names_by_type: dict[UUID, dict[str, str]] = defaultdict(dict)
        for item in names:
            names_by_type[item.product_type_id][item.locale_code] = item.name
        names_by_block: dict[UUID, dict[str, str]] = defaultdict(dict)
        for block_translation in block_translations:
            names_by_block[block_translation.block_id][
                block_translation.locale_code
            ] = block_translation.name
        blocks_by_type: dict[UUID, list[SchemaBlockDTO]] = defaultdict(list)
        for assignment, definition in assignments:
            blocks_by_type[assignment.product_type_id].append(
                SchemaBlockDTO(
                    definition.id,
                    definition.code,
                    ContentBlockType(definition.type),
                    ContentScope(assignment.scope),
                    assignment.required,
                    assignment.position,
                    dict(names_by_block[definition.id]),
                )
            )
        return tuple(
            ProductTypeSchemaDTO(
                item.id,
                item.code,
                item.is_system,
                item.schema_version,
                dict(names_by_type[item.id]),
                tuple(blocks_by_type[item.id]),
            )
            for item in types
        )
