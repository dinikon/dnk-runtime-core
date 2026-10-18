from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.crm.application.company.query.get_company.dto import CompanyDetailsDTO
from src.modules.crm.domain.contact.value_object.identifier import ContactIdVO
from src.modules.crm.infrastructure.company.persistence.query_mapper import (
    CompanyQueryMapper,
)
from src.modules.crm.infrastructure.persistence.models.company import CompanyModel
from src.modules.crm.infrastructure.persistence.models.contact import ContactModel
from src.modules.crm.infrastructure.persistence.models.contact_company import (
    ContactCompanyModel,
)


class SqlAlchemyContactCompanyQueryRepository:
    """Читает компании контакта одной проекцией с внешним соединением."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_companies(
        self, contact_id: ContactIdVO
    ) -> list[CompanyDetailsDTO] | None:
        contact = ContactModel.__table__
        link = ContactCompanyModel.__table__
        company = CompanyModel.__table__
        result = await self._session.execute(
            select(
                contact.c.id.label("owner_id"),
                company.c.id.label("id"),
                company.c.legal_name.label("legal_name"),
                company.c.created_at.label("created_at"),
                company.c.updated_at.label("updated_at"),
                company.c.created_by.label("created_by"),
                company.c.updated_by.label("updated_by"),
            )
            .select_from(
                contact.outerjoin(link, contact.c.id == link.c.contact_id).outerjoin(
                    company, link.c.company_id == company.c.id
                )
            )
            .where(contact.c.id == contact_id.uuid)
            .order_by(company.c.created_at, company.c.id)
        )
        rows = result.mappings().all()
        if not rows:
            return None
        return [
            CompanyQueryMapper.to_details(row) for row in rows if row["id"] is not None
        ]
