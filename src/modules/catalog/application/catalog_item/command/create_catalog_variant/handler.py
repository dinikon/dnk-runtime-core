from src.modules.catalog.application.catalog_item.command.create_catalog_variant.command import (
    CreateCatalogVariantCommand,
)
from src.modules.catalog.application.catalog_item.command.create_catalog_variant.dto import (
    CreateCatalogVariantResultDTO,
)
from src.modules.catalog.application.catalog_item.creation_service import (
    CatalogItemCreationService,
)
from src.modules.catalog.application.catalog_item.mutation_service import (
    CatalogItemMutationService,
)


class CreateCatalogVariantHandler:
    """Добавляет entity через агрегат под общей блокировкой родителя."""

    def __init__(
        self,
        mutations: CatalogItemMutationService,
        creation: CatalogItemCreationService,
    ) -> None:
        """Принимает координатор и подготовку значений одного UoW."""
        self._mutations, self._creation = mutations, creation

    async def execute(
        self, command: CreateCatalogVariantCommand
    ) -> CreateCatalogVariantResultDTO:
        """Сохраняет вариант и audit родителя атомарно без своего commit."""
        root = await self._mutations.load(command.tenant_id, command.item_id)
        schema = await self._creation.schemas.get_by_id(root.product_type_id)
        variant = await self._creation.prepare_variant(
            tenant_id=command.tenant_id,
            actor_id=command.actor_id,
            parent=root,
            values=command.product,
            schema=schema,
        )
        root.add_variant(
            variant=variant,
            actor=command.actor_id,
            now=self._creation.clock.now(),
            schema=schema,
        )
        await self._mutations.save(root)
        return CreateCatalogVariantResultDTO(variant.id.uuid, root.id.uuid)
