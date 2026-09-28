from dataclasses import fields
from sqlalchemy import select, func, exists
from src.modules.crm.application.company.dto import CompanyDetailsDTO, CompanyPageDTO
from src.modules.crm.application.links.dto import CrmLinkDTO
from src.modules.crm.domain.contact.value_object import ContactIdVO
from .base import CrmSessionRepository
from .models import ContactModel, CompanyModel, ContactCompanyModel
from .query_mappers import company_projection


class SqlAlchemyCompanyQueryRepository(CrmSessionRepository):
    async def get_details(self, tenant_id, identifier):
        table = CompanyModel.__table__
        options = self.execution_options(tenant_id)
        result = await self.session.execute(
            select(table)
            .where(table.c.id == identifier.uuid)
            .execution_options(**options)
        )
        row = result.mappings().one_or_none()
        if row is None:
            return None
        base = company_projection(row)
        target, links = ContactModel.__table__, ContactCompanyModel.__table__
        name = func.concat_ws(
            " ", target.c.last_name, target.c.first_name, target.c.middle_name
        )
        result = await self.session.execute(
            select(target.c.id, name.label("display_name"))
            .select_from(target.join(links, links.c.contact_id == target.c.id))
            .where(links.c.company_id == identifier.uuid)
            .order_by(func.lower(name), target.c.id)
            .execution_options(**options)
        )
        related = tuple(
            CrmLinkDTO(ContactIdVO.from_value(item["id"]), item["display_name"])
            for item in result.mappings()
        )
        return CompanyDetailsDTO(
            **{field.name: getattr(base, field.name) for field in fields(base)},
            contacts=related,
        )

    async def list(self, query):
        return await self._list(query)

    async def list_available(self, query):
        owner = ContactModel.__table__
        found = await self.session.scalar(
            select(owner.c.id)
            .where(owner.c.id == query.contact_id.uuid)
            .execution_options(**self.execution_options(query.tenant_id))
        )
        if found is None:
            return None
        return await self._list(query, query.contact_id)

    async def _list(self, query, owner_id=None):
        table = CompanyModel.__table__
        clauses = []
        q = query.q.strip()
        if q:
            clauses.append(table.c.name.ilike(f"%{q}%"))
        if owner_id is not None:
            links = ContactCompanyModel.__table__
            clauses.append(
                ~exists(
                    select(1).where(
                        links.c.company_id == table.c.id,
                        links.c.contact_id == owner_id.uuid,
                    )
                )
            )
        options = self.execution_options(query.tenant_id)
        total = int(
            await self.session.scalar(
                select(func.count())
                .select_from(table)
                .where(*clauses)
                .execution_options(**options)
            )
            or 0
        )
        result = await self.session.execute(
            select(table)
            .where(*clauses)
            .order_by(func.lower(table.c.name), table.c.id)
            .offset(query.offset)
            .limit(query.limit)
            .execution_options(**options)
        )
        return CompanyPageDTO(
            items=tuple(company_projection(row) for row in result.mappings()),
            total=total,
            limit=query.limit,
            offset=query.offset,
        )

    async def linked_contact_ids(self, tenant_id, company_id):
        table = ContactCompanyModel.__table__
        result = await self.session.scalars(
            select(table.c.contact_id)
            .where(table.c.company_id == company_id.uuid)
            .order_by(table.c.contact_id)
            .execution_options(**self.execution_options(tenant_id))
        )
        return tuple(ContactIdVO.from_value(value) for value in result)
