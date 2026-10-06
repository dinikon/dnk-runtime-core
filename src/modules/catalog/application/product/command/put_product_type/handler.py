from src.modules.catalog.application.content_schema.contracts import (
    ContentSchemaRepositoryProtocol,
)
from src.modules.catalog.application.content_schema.service import (
    SchemaConflictError,
    SchemaNotFoundError,
)
from src.modules.catalog.application.product.command.put_product_type.command import (
    PutProductTypeCommand,
)
from src.modules.catalog.application.product.command.put_product_type.dto import (
    PutProductTypeResultDTO,
)
from src.modules.catalog.domain.product.error import ProductNotFoundError
from src.modules.catalog.domain.product.repository import ProductRepositoryProtocol
from src.modules.catalog.domain.product_type.aggregate import ContentScope
from src.modules.shared.domain.time.clock_port import ClockPort


class PutProductTypeHandler:
    def __init__(
        self,
        products: ProductRepositoryProtocol,
        schemas: ContentSchemaRepositoryProtocol,
        clock: ClockPort,
    ) -> None:
        self._products, self._schemas, self._clock = products, schemas, clock

    async def execute(self, command: PutProductTypeCommand) -> PutProductTypeResultDTO:
        product = await self._products.get_for_update(command.product_id)
        if product is None:
            raise ProductNotFoundError("Product not found.")
        schema = await self._schemas.get_type(command.product_type_id.uuid, lock=True)
        if schema is None:
            raise SchemaNotFoundError("Product type not found.")
        if schema.schema_version != command.expected_schema_version:
            raise SchemaConflictError("Product type schema version changed.")
        for scope, contents in [
            (ContentScope.PRODUCT, product.contents),
            *[(ContentScope.VARIANT, variant.contents) for variant in product.variants],
        ]:
            allowed = {item.block_id for item in schema.blocks if item.scope is scope}
            required = {
                item.block_id
                for item in schema.blocks
                if item.scope is scope and item.required
            }
            for content in contents.values():
                saved = set(content.values)
                if not saved <= allowed or not required <= saved:
                    raise SchemaConflictError(
                        "Saved content is incompatible with product type."
                    )
        product.change_product_type(
            command.product_type_id, actor_id=command.actor_id, now=self._clock.now()
        )
        await self._products.save_type(product)
        return PutProductTypeResultDTO(
            product.id.uuid, schema.id, schema.schema_version
        )
