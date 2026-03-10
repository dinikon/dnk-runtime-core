from dataclasses import dataclass

from src.modules.crm.domain.error import DealTitleRequiredError
from src.modules.crm.domain.shared.crm_entity_id import CrmEntityIdVO


class DealIdVO(CrmEntityIdVO): ...


@dataclass(frozen=True, slots=True)
class DealTitleVO:
    value: str

    def __post_init__(self) -> None:
        normalized = self.value.strip()
        if not normalized:
            raise DealTitleRequiredError()
        object.__setattr__(self, "value", normalized)


__all__ = ["DealIdVO", "DealTitleVO"]
