from dataclasses import dataclass

from src.modules.crm.domain.company.value_object import CompanyIdVO
from src.modules.shared import EntityIdVO


@dataclass(slots=True, frozen=True)
class DeleteCompanyCommand:
    """Команда application-слоя на удаление компании tenant."""

    tenant_id: EntityIdVO
    company_id: CompanyIdVO
