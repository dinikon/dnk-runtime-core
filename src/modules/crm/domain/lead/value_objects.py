from dataclasses import dataclass

from src.modules.crm.domain.error import LeadTitleRequiredError
from src.modules.crm.domain.shared.crm_entity_id import CrmEntityId


class LeadId(CrmEntityId): ...


@dataclass(frozen=True, slots=True)
class LeadTitle:
    value: str

    def __post_init__(self) -> None:
        normalized = self.value.strip()
        if not normalized:
            raise LeadTitleRequiredError()
        object.__setattr__(self, "value", normalized)


__all__ = ["LeadId", "LeadTitle"]
