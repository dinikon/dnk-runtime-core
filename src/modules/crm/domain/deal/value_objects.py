from dataclasses import dataclass

from src.modules.crm.domain.error import DealTitleRequiredError
from src.modules.crm.domain.shared.crm_entity_id import CrmEntityId


class DealId(CrmEntityId): ...


@dataclass(frozen=True, slots=True)
class DealTitle:
    value: str

    def __post_init__(self) -> None:
        normalized = self.value.strip()
        if not normalized:
            raise DealTitleRequiredError()
        object.__setattr__(self, "value", normalized)
