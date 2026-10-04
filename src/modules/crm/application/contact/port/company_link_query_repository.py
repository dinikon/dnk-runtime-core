from typing import Protocol

from src.modules.crm.application.company.query.get_company.dto import CompanyDetailsDTO
from src.modules.crm.domain.contact.value_object.identifier import ContactIdVO


class ContactCompanyQueryRepositoryProtocol(Protocol):
    """Список компаний контакта; None означает отсутствие самого контакта."""

    async def list_companies(
        self, contact_id: ContactIdVO
    ) -> list[CompanyDetailsDTO] | None: ...
