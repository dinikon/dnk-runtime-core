from typing import Protocol

from src.modules.catalog.domain.attribute.aggregate import Attribute


class AttributeRepositoryProtocol(Protocol):
    async def add(self, attribute: Attribute) -> None: ...
