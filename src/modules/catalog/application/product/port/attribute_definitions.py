from typing import Protocol
from src.modules.catalog.domain.attribute.value_object.identifier import AttributeIdVO
from src.modules.catalog.domain.product.value_object.attribute_snapshot import (
    EnumAttributeSnapshot,
)


class AttributeDefinitionsPort(Protocol):
    """Предоставляет необходимые Product immutable снимки определений."""

    async def get_definitions(
        self, identifiers: tuple[AttributeIdVO, ...]
    ) -> tuple[EnumAttributeSnapshot, ...]:
        """Проверяет наличие определений и возвращает допустимые option ID."""
        ...
