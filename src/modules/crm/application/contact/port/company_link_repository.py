from typing import Protocol

from src.modules.crm.domain.company.value_object.identifier import CompanyIdVO
from src.modules.crm.domain.contact.value_object.company_link import (
    ContactCompanyLinkVO,
)
from src.modules.crm.domain.contact.value_object.identifier import ContactIdVO


class CompanyLinkRepositoryProtocol(Protocol):
    """Запись членства компании на сессии текущего tenant."""

    async def lock_contact(self, contact_id: ContactIdVO) -> bool: ...

    async def lock_company(self, company_id: CompanyIdVO) -> bool: ...

    async def link(self, link: ContactCompanyLinkVO) -> None: ...

    async def unlink(self, link: ContactCompanyLinkVO) -> None: ...
