from src.modules.inventory.domain.category.entity import CategoryEntity
from src.modules.inventory.domain.category.error import (
    CategoryHierarchyError,
    CategoryNotFoundError,
)
from src.modules.inventory.domain.category.repository import (
    CategoryCommandRepositoryProtocol,
)
from src.modules.inventory.domain.category.value_object import CategoryIdVO
from src.modules.shared import EntityIdVO
from src.modules.shared.domain.time import ClockPort


class CategoryService:
    """Доменный сервис сценариев создания, обновления и удаления категорий."""

    def __init__(
        self,
        *,
        command_repository: CategoryCommandRepositoryProtocol,
        clock: ClockPort,
    ) -> None:
        """Инициализирует сервис командным репозиторием и clock-портом."""
        self._command_repository = command_repository
        self._clock = clock

    async def create_category(
        self,
        *,
        tenant_id: EntityIdVO,
        category_id: CategoryIdVO,
        name: str,
        parent_category_id: CategoryIdVO | None = None,
    ) -> CategoryEntity:
        """Создает категорию после проверки parent-ссылки."""
        await self._ensure_valid_parent(
            tenant_id=tenant_id,
            category_id=category_id,
            parent_category_id=parent_category_id,
        )
        now = self._clock.now()
        category = CategoryEntity.create(
            id_=category_id,
            now=now,
            name=name,
            parent_category_id=parent_category_id,
        )
        return await self._command_repository.save(
            tenant_id=tenant_id,
            category=category,
        )

    async def get_category(
        self,
        *,
        tenant_id: EntityIdVO,
        category_id: CategoryIdVO,
    ) -> CategoryEntity:
        """Возвращает категорию tenant или поднимает CategoryNotFoundError."""
        category = await self._command_repository.load(
            tenant_id=tenant_id,
            category_id=category_id,
        )
        if category is None:
            raise CategoryNotFoundError(str(category_id))
        return category

    async def update_category(
        self,
        *,
        tenant_id: EntityIdVO,
        category_id: CategoryIdVO,
        name: str,
        parent_category_id: CategoryIdVO | None = None,
    ) -> CategoryEntity:
        """Загружает категорию, проверяет parent и сохраняет обновленную entity."""
        category = await self.get_category(
            tenant_id=tenant_id,
            category_id=category_id,
        )
        await self._ensure_valid_parent(
            tenant_id=tenant_id,
            category_id=category_id,
            parent_category_id=parent_category_id,
        )
        category.update(
            now=self._clock.now(),
            name=name,
            parent_category_id=parent_category_id,
        )
        return await self._command_repository.save(
            tenant_id=tenant_id,
            category=category,
        )

    async def delete_category(
        self,
        *,
        tenant_id: EntityIdVO,
        category_id: CategoryIdVO,
    ) -> None:
        """Проверяет существование категории и удаляет ее из repository."""
        await self.get_category(
            tenant_id=tenant_id,
            category_id=category_id,
        )
        await self._command_repository.delete(
            tenant_id=tenant_id,
            category_id=category_id,
        )

    async def _ensure_valid_parent(
        self,
        *,
        tenant_id: EntityIdVO,
        category_id: CategoryIdVO,
        parent_category_id: CategoryIdVO | None,
    ) -> None:
        """Проверяет parent на существование, self-parent и циклы."""
        if parent_category_id is None:
            return
        if parent_category_id == category_id:
            raise CategoryHierarchyError("Product category cannot be its own parent.")

        seen_ids = {category_id.uuid}
        cursor = await self._command_repository.load(
            tenant_id=tenant_id,
            category_id=parent_category_id,
        )
        if cursor is None:
            raise CategoryNotFoundError(str(parent_category_id))

        while cursor is not None:
            if cursor.id.uuid in seen_ids:
                raise CategoryHierarchyError("Product category tree cycle detected.")
            seen_ids.add(cursor.id.uuid)
            if cursor.parent_category_id is None:
                return
            cursor = await self._command_repository.load(
                tenant_id=tenant_id,
                category_id=cursor.parent_category_id,
            )
            if cursor is None:
                raise CategoryNotFoundError(str(parent_category_id))
