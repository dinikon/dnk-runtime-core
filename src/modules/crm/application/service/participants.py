from dataclasses import dataclass
from uuid import UUID
from src.modules.crm.domain.contact.repository import ContactRepositoryProtocol
from src.modules.crm.domain.company.repository import CompanyRepositoryProtocol
from src.modules.crm.domain.contact.value_object.identifier import ContactIdVO
from src.modules.crm.domain.company.value_object.identifier import CompanyIdVO
from src.modules.crm.application.contact.port.company_link_query_repository import (
    ContactCompanyQueryRepositoryProtocol,
)
from src.modules.crm.domain.sales_error import SalesNotFoundError


@dataclass(frozen=True, slots=True)
class ContactSnapshotDTO:
    """Разрешённые данные контакта для копирования в новое обращение."""

    first_name: str
    last_name: str | None
    middle_name: str | None


class ParticipantsService:
    """Координирует существующие агрегаты CRM без скрытой перезаписи."""

    def __init__(
        self,
        contacts: ContactRepositoryProtocol,
        companies: CompanyRepositoryProtocol,
        links: ContactCompanyQueryRepositoryProtocol,
    ) -> None:
        """Принимает контракты существующих агрегатов."""
        self.contacts = contacts
        self.companies = companies
        self.links = links

    async def contact(self, record_id: UUID) -> ContactSnapshotDTO:
        """Проверяет существование и возвращает собственный снимок."""
        entity = await self.contacts.get_for_update(ContactIdVO.from_value(record_id))
        if entity is None:
            raise SalesNotFoundError("Контакт не найден.")
        return ContactSnapshotDTO(
            entity.name.first_name, entity.name.last_name, entity.name.middle_name
        )

    async def validate(
        self, contact_ids: tuple[UUID, ...], company_ids: tuple[UUID, ...]
    ) -> None:
        """Стабильно блокирует участников текущего tenant."""
        for record_id in sorted(set(contact_ids), key=str):
            await self.contact(record_id)
        for record_id in sorted(set(company_ids), key=str):
            if (
                await self.companies.get_for_update(CompanyIdVO.from_value(record_id))
                is None
            ):
                raise SalesNotFoundError("Компания не найдена.")
