from typing import Mapping, Protocol
from uuid import UUID


class AttributeReaderPort(Protocol):
    async def option_ids(
        self, attribute_ids: frozenset[UUID]
    ) -> Mapping[UUID, frozenset[UUID]]: ...
