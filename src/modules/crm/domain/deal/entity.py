from dataclasses import dataclass
from typing import Self

from src.modules.crm.domain.deal.value_objects import DealIdVO, DealTitleVO


@dataclass(slots=True)
class DealEntity:
    id: DealIdVO
    title: DealTitleVO

    @classmethod
    def create(cls, *, title: str) -> Self:
        return cls(id=DealIdVO.new(), title=DealTitleVO(title))

    def rename(self, *, title: str) -> None:
        self.title = DealTitleVO(title)


__all__ = ["DealEntity"]
