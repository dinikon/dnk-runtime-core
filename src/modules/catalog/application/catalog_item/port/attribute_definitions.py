from typing import Protocol
from src.modules.catalog.domain.attribute.value_object.identifier import AttributeIdVO
from src.modules.catalog.domain.catalog_item.value_object.attribute_snapshot import (
    EnumAttributeSnapshot,
)


class AttributeDefinitionsPort(Protocol):
    """Читает минимальные immutable снимки разрешённых enum-options."""

    async def get_definitions(
        self, identifiers: tuple[AttributeIdVO, ...]
    ) -> tuple[EnumAttributeSnapshot, ...]:
        """Возвращает definitions либо сообщает об отсутствующем ID."""
        ...
