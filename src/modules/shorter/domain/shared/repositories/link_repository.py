from typing import Protocol

from src.modules.shorter.domain.link.entity import LinkEntity


class LinkRepositoryPort(Protocol):
    def save(self, link: LinkEntity) -> None: ...
