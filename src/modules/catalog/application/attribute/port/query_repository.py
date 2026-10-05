from typing import Protocol

from src.modules.catalog.application.attribute.query.list_attributes.dto import (
    AttributeDetailsDTO,
)
from src.modules.catalog.domain.attribute.locale import AttributeLocaleVO
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


class AttributeQueryRepositoryProtocol(Protocol):
    async def list_details(
        self, locale: AttributeLocaleVO
    ) -> tuple[AttributeDetailsDTO, ...]: ...

    async def get_details(
        self, attribute_id: EntityIdVO, locale: AttributeLocaleVO
    ) -> AttributeDetailsDTO | None: ...
