from dataclasses import dataclass
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


@dataclass(frozen=True, slots=True)
class CreateTenantAdminCommand:
    tenant_id: EntityIdVO
    first_name: str
    last_name: str
    email: str
