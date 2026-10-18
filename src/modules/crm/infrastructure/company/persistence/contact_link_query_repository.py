from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.crm.application.contact.query.get_contact.dto import ContactDetailsDTO
from src.modules.crm.domain.company.value_object.identifier import CompanyIdVO
from src.modules.crm.infrastructure.contact.persistence.query_mapper import (
    ContactQueryMapper,
)
from src.modules.crm.infrastructure.persistence.models.company import CompanyModel
from src.modules.crm.infrastructure.persistence.models.contact import ContactModel
from src.modules.crm.infrastructure.persistence.models.contact_company import (
    ContactCompanyModel,
)


class SqlAlchemyCompanyContactQueryRepository:
    """Читает контакты компании одной проекцией с внешним соединением."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_contacts(
        self, company_id: CompanyIdVO
    ) -> list[ContactDetailsDTO] | None:
        company = CompanyModel.__table__
        link = ContactCompanyModel.__table__
        contact = ContactModel.__table__
        result = await self._session.execute(
            select(
                company.c.id.label("owner_id"),
                contact.c.id.label("id"),
                contact.c.first_name.label("first_name"),
                contact.c.last_name.label("last_name"),
                contact.c.middle_name.label("middle_name"),
                contact.c.created_at.label("created_at"),
                contact.c.updated_at.label("updated_at"),
                contact.c.created_by.label("created_by"),
                contact.c.updated_by.label("updated_by"),
            )
            .select_from(
                company.outerjoin(link, company.c.id == link.c.company_id).outerjoin(
                    contact, link.c.contact_id == contact.c.id
                )
            )
            .where(company.c.id == company_id.uuid)
            .order_by(contact.c.created_at, contact.c.id)
        )
        rows = result.mappings().all()
        if not rows:
            return None
        return [
            ContactQueryMapper.to_details(row) for row in rows if row["id"] is not None
        ]
