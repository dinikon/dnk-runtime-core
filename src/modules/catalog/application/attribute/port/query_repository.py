from typing import Protocol
from src.modules.catalog.domain.attribute.value_object.identifier import AttributeIdVO
from src.modules.catalog.application.attribute.query.get_attribute.dto import (
    GetAttributeDetailsDTO,
)
from src.modules.catalog.application.attribute.query.list_attributes.dto import (
    ListAttributesPageDTO,
)


class AttributeQueryRepositoryProtocol(Protocol):
    """Чтение отдельных проекций enum-справочника."""

    async def get_details(
        self, identifier: AttributeIdVO, locale: str
    ) -> GetAttributeDetailsDTO | None:
        """Читает определение с options и явной locale без fallback."""
        ...

    async def list_page(
        self, locale: str, search: str, page: int, page_size: int
    ) -> ListAttributesPageDTO:
        """Возвращает страницу определений с устойчивым порядком."""
        ...
