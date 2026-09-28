from dataclasses import dataclass
from src.modules.crm.domain.contact.value_object import ContactIdVO
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


@dataclass(frozen=True, slots=True)
class ListAvailableCompaniesQuery:
    tenant_id: EntityIdVO
    contact_id: ContactIdVO
    q: str = ""
    limit: int = 25
    offset: int = 0
