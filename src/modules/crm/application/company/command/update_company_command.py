from dataclasses import dataclass

from src.modules.crm.domain.company.value_object import CompanyIdVO
from src.modules.shared import EntityIdVO


@dataclass(slots=True, frozen=True)
class UpdateCompanyCommand:
    """Команда application-слоя на обновление компании tenant."""

    tenant_id: EntityIdVO
    company_id: CompanyIdVO
    legal_name: str
