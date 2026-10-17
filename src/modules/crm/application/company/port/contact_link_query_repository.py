from typing import Protocol

from src.modules.crm.application.contact.query.get_contact.dto import ContactDetailsDTO
from src.modules.crm.domain.company.value_object.identifier import CompanyIdVO


class CompanyContactQueryRepositoryProtocol(Protocol):
    """Список контактов компании; None означает отсутствие самой компании."""

    async def list_contacts(
        self, company_id: CompanyIdVO
    ) -> list[ContactDetailsDTO] | None: ...
