from dataclasses import dataclass
from typing import Self

from src.modules.crm.domain.deal.value_objects import DealId, DealTitle


@dataclass(slots=True)
class Deal:
    id: DealId
    title: DealTitle

    @classmethod
    def create(cls, *, title: str) -> Self:
        return cls(id=DealId.new(), title=DealTitle(title))

    def rename(self, *, title: str) -> None:
        self.title = DealTitle(title)
