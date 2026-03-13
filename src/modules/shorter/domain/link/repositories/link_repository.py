from typing import Protocol

from src.modules.shared import EntityIdVO
from src.modules.shorter.domain.link.entity import LinkEntity
from src.modules.shorter.domain.link.value_object import LinkIdVO


class LinkRepositoryPort(Protocol):
    async def save(self, link: LinkEntity) -> None: ...

    async def get_by_id(
        self,
        *,
        domain_id: EntityIdVO,
        link_id: LinkIdVO,
    ) -> LinkEntity | None: ...
