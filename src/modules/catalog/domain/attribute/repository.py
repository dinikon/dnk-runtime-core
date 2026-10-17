from typing import Protocol
from src.modules.catalog.domain.attribute.aggregate import AttributeDefinition
from src.modules.catalog.domain.attribute.value_object.identifier import AttributeIdVO
from src.modules.catalog.domain.attribute.value_object.option_id import (
    AttributeOptionIdVO,
)


class AttributeRepositoryProtocol(Protocol):
    """Хранение полного агрегата и проверка ссылок в общем tenant UoW."""

    async def get(self, identifier: AttributeIdVO) -> AttributeDefinition:
        """Восстанавливает определение либо сообщает об отсутствии."""
        ...

    async def add(self, entity: AttributeDefinition) -> None:
        """Добавляет агрегат без commit."""
        ...

    async def save(self, entity: AttributeDefinition) -> None:
        """Сохраняет определение и options без commit."""
        ...

    async def delete(self, entity: AttributeDefinition) -> None:
        """Удаляет проверенное определение без commit."""
        ...

    async def is_used(self, identifier: AttributeIdVO) -> bool:
        """Проверяет использование определения в осях."""
        ...

    async def used_options(
        self, identifier: AttributeIdVO
    ) -> frozenset[AttributeOptionIdVO]:
        """Возвращает все разрешённые значения осей, включая не выбранные позицией."""
        ...
