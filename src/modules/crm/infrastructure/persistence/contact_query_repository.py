from dataclasses import fields
from sqlalchemy import select, func, or_, exists
from src.modules.crm.application.contact.dto import ContactDetailsDTO, ContactPageDTO
from src.modules.crm.application.links.dto import CrmLinkDTO
from src.modules.crm.domain.company.value_object import CompanyIdVO
from .base import CrmSessionRepository
from .models import ContactModel, CompanyModel, ContactCompanyModel
from .query_mappers import contact_projection


class SqlAlchemyContactQueryRepository(CrmSessionRepository):
    async def get_details(self, tenant_id, identifier):
        table = ContactModel.__table__
        options = self.execution_options(tenant_id)
        result = await self.session.execute(
            select(table)
            .where(table.c.id == identifier.uuid)
            .execution_options(**options)
        )
        row = result.mappings().one_or_none()
        if row is None:
            return None
        base = contact_projection(row)
        target, links = CompanyModel.__table__, ContactCompanyModel.__table__
        name = target.c.name
        result = await self.session.execute(
            select(target.c.id, name.label("display_name"))
            .select_from(target.join(links, links.c.company_id == target.c.id))
            .where(links.c.contact_id == identifier.uuid)
            .order_by(func.lower(name), target.c.id)
            .execution_options(**options)
        )
        related = tuple(
            CrmLinkDTO(CompanyIdVO.from_value(item["id"]), item["display_name"])
            for item in result.mappings()
        )
        return ContactDetailsDTO(
            **{field.name: getattr(base, field.name) for field in fields(base)},
            companies=related,
        )

    async def list(self, query):
        return await self._list(query)

    async def list_available(self, query):
        owner = CompanyModel.__table__
        found = await self.session.scalar(
            select(owner.c.id)
            .where(owner.c.id == query.company_id.uuid)
            .execution_options(**self.execution_options(query.tenant_id))
        )
        if found is None:
            return None
        return await self._list(query, query.company_id)

    async def _list(self, query, owner_id=None):
        table = ContactModel.__table__
        clauses = []
        q = query.q.strip()
        if q:
            pattern = f"%{q}%"
            clauses.append(
                or_(
                    table.c.first_name.ilike(pattern),
                    table.c.last_name.ilike(pattern),
                    table.c.middle_name.ilike(pattern),
                    func.concat_ws(
                        " ", table.c.last_name, table.c.first_name, table.c.middle_name
                    ).ilike(pattern),
                )
            )
        if owner_id is not None:
            links = ContactCompanyModel.__table__
            clauses.append(
                ~exists(
                    select(1).where(
                        links.c.contact_id == table.c.id,
                        links.c.company_id == owner_id.uuid,
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
            .order_by(
                func.lower(func.coalesce(table.c.last_name, "")),
                func.lower(table.c.first_name),
                func.lower(func.coalesce(table.c.middle_name, "")),
                table.c.id,
            )
            .offset(query.offset)
            .limit(query.limit)
            .execution_options(**options)
        )
        return ContactPageDTO(
            items=tuple(contact_projection(row) for row in result.mappings()),
            total=total,
            limit=query.limit,
            offset=query.offset,
        )
