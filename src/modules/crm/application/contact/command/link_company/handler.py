from src.modules.crm.application.contact.command.link_company.command import (
    LinkCompanyCommand,
)
from src.modules.crm.application.contact.port.company_link_repository import (
    CompanyLinkRepositoryProtocol,
)
from src.modules.crm.domain.company.error import CompanyNotFoundError
from src.modules.crm.domain.contact.error import ContactNotFoundError
from src.modules.crm.domain.contact.value_object.company_link import (
    ContactCompanyLinkVO,
)


class LinkCompanyHandler:
    """Связывает существующие агрегаты в транзакции внешнего UoW."""

    def __init__(self, repository: CompanyLinkRepositoryProtocol) -> None:
        self._repository = repository

    async def execute(self, command: LinkCompanyCommand) -> None:
        # Оба направления HTTP используют один порядок блокировки.
        if not await self._repository.lock_contact(command.contact_id):
            raise ContactNotFoundError("Contact not found.")
        if not await self._repository.lock_company(command.company_id):
            raise CompanyNotFoundError("Company not found.")
        await self._repository.link(
            ContactCompanyLinkVO(command.contact_id, command.company_id)
        )
