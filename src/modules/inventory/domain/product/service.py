from src.modules.inventory.domain.category.error import CategoryNotFoundError
from src.modules.inventory.domain.category.repository import (
    CategoryCommandRepositoryProtocol,
)
from src.modules.inventory.domain.category.value_object import CategoryIdVO
from src.modules.inventory.domain.product.entity import ProductEntity
from src.modules.inventory.domain.product.error import ProductNotFoundError
from src.modules.inventory.domain.product.repository import (
    ProductCommandRepositoryProtocol,
)
from src.modules.inventory.domain.product.value_object import ProductIdVO
from src.modules.shared import EntityIdVO
from src.modules.shared.domain.time import ClockPort


class ProductService:
    """Доменный сервис сценариев создания, обновления и удаления товаров."""

    def __init__(
        self,
        *,
        command_repository: ProductCommandRepositoryProtocol,
        category_repository: CategoryCommandRepositoryProtocol,
        clock: ClockPort,
    ) -> None:
        """Инициализирует сервис репозиториями и clock-портом."""
        self._command_repository = command_repository
        self._category_repository = category_repository
        self._clock = clock

    async def create_product(
        self,
        *,
        tenant_id: EntityIdVO,
        product_id: ProductIdVO,
        sku: str,
        product_name: str,
        description: str | None = None,
        category_id: CategoryIdVO | None = None,
    ) -> ProductEntity:
        """Создает доменную entity товара и сохраняет ее."""
        await self._ensure_category_exists(
            tenant_id=tenant_id,
            category_id=category_id,
        )
        now = self._clock.now()
        product = ProductEntity.create(
            id_=product_id,
            now=now,
            sku=sku,
            product_name=product_name,
            description=description,
            category_id=category_id,
        )
        return await self._command_repository.save(
            tenant_id=tenant_id,
            product=product,
        )

    async def get_product(
        self,
        *,
        tenant_id: EntityIdVO,
        product_id: ProductIdVO,
    ) -> ProductEntity:
        """Возвращает товар tenant или поднимает ProductNotFoundError."""
        product = await self._command_repository.load(
            tenant_id=tenant_id,
            product_id=product_id,
        )
        if product is None:
            raise ProductNotFoundError(str(product_id))
        return product

    async def update_product(
        self,
        *,
        tenant_id: EntityIdVO,
        product_id: ProductIdVO,
        sku: str,
        product_name: str,
        description: str | None = None,
        category_id: CategoryIdVO | None = None,
    ) -> ProductEntity:
        """Загружает товар, применяет изменения и сохраняет обновленную entity."""
        await self._ensure_category_exists(
            tenant_id=tenant_id,
            category_id=category_id,
        )
        product = await self.get_product(
            tenant_id=tenant_id,
            product_id=product_id,
        )
        product.update(
            now=self._clock.now(),
            sku=sku,
            product_name=product_name,
            description=description,
            category_id=category_id,
        )
        return await self._command_repository.save(
            tenant_id=tenant_id,
            product=product,
        )

    async def delete_product(
        self,
        *,
        tenant_id: EntityIdVO,
        product_id: ProductIdVO,
    ) -> None:
        """Проверяет существование товара и удаляет его из repository."""
        await self.get_product(
            tenant_id=tenant_id,
            product_id=product_id,
        )
        await self._command_repository.delete(
            tenant_id=tenant_id,
            product_id=product_id,
        )

    async def _ensure_category_exists(
        self,
        *,
        tenant_id: EntityIdVO,
        category_id: CategoryIdVO | None,
    ) -> None:
        """Проверяет существование категории, если товар ссылается на нее."""
        if category_id is None:
            return
        category = await self._category_repository.load(
            tenant_id=tenant_id,
            category_id=category_id,
        )
        if category is None:
            raise CategoryNotFoundError(str(category_id))
