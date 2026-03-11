from dataclasses import dataclass

from modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.crm.domain.error import DealTitleRequiredError


class DealIdVO(EntityIdVO): ...


@dataclass(frozen=True, slots=True)
class DealTitleVO:
    value: str

    def __post_init__(self) -> None:
        normalized = self.value.strip()
        if not normalized:
            raise DealTitleRequiredError()
        object.__setattr__(self, "value", normalized)


__all__ = ["DealIdVO", "DealTitleVO"]
