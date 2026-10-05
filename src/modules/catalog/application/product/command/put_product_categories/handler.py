from src.modules.catalog.application.product.command.put_product_categories.command import (
    PutProductCategoriesCommand,
)
from src.modules.catalog.application.product.command.put_product_categories.dto import (
    PutProductCategoriesResultDTO,
)
from src.modules.catalog.application.product.port.category_reader import (
    CategoryReaderPort,
)
from src.modules.catalog.domain.category.value_object.identifier import CategoryIdVO
from src.modules.catalog.domain.product.error import ProductNotFoundError
from src.modules.catalog.domain.product.repository import ProductRepositoryProtocol
from src.modules.shared.domain.time.clock_port import ClockPort


class PutProductCategoriesHandler:
    def __init__(
        self,
        repository: ProductRepositoryProtocol,
        categories: CategoryReaderPort,
        clock: ClockPort,
    ) -> None:
        self._repository, self._categories, self._clock = repository, categories, clock

    async def execute(
        self, command: PutProductCategoriesCommand
    ) -> PutProductCategoriesResultDTO:
        product = await self._repository.get_for_update(command.product_id)
        if product is None:
            raise ProductNotFoundError("Product not found.")
        product.replace_categories(
            category_ids=tuple(
                CategoryIdVO.from_value(item) for item in command.category_ids
            ),
            primary_category_id=(
                CategoryIdVO.from_value(command.primary_category_id)
                if command.primary_category_id
                else None
            ),
            actor_id=command.actor_id,
            now=self._clock.now(),
        )
        await self._categories.require_all(command.category_ids)
        await self._repository.save_categories(product)
        return PutProductCategoriesResultDTO(
            product.id.uuid,
            tuple(item.uuid for item in product.category_ids),
            product.primary_category_id.uuid if product.primary_category_id else None,
            product.updated_at,
            product.updated_by.uuid,
        )
