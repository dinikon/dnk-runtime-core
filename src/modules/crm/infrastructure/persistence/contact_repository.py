from datetime import datetime

from sqlalchemy import delete, func, insert, or_, select, update

from src.modules.crm.application.contact.dto import ContactPageDTO, contact_dto
from src.modules.crm.application.contact.query import ListContactsQuery
from src.modules.crm.domain.contact import (
    Contact,
    ContactIdVO,
    ContactNameVO,
    ContactNotFoundError,
)
from src.modules.crm.infrastructure.persistence.base import (
    CrmSessionRepository,
    checked,
    identifier,
)
from src.modules.crm.infrastructure.persistence.models import ContactModel


def contact_entity(row) -> Contact:
    """Явно мапит persistence row в Contact aggregate."""
    return Contact(
        id=identifier(row["id"], ContactIdVO),
        name=ContactNameVO(
            first_name=checked(row["first_name"], str),
            last_name=checked(row["last_name"], str, optional=True),
            middle_name=checked(row["middle_name"], str, optional=True),
        ),
        created_at=checked(row["created_at"], datetime),
        updated_at=checked(row["updated_at"], datetime),
        created_by=identifier(row["created_by"]),
        updated_by=identifier(row["updated_by"]),
    )


def contact_values(contact: Contact) -> dict[str, object]:
    """Преобразует Contact aggregate в persistence primitives."""
    return {
        "id": contact.id.uuid,
        "first_name": contact.name.first_name,
        "last_name": contact.name.last_name,
        "middle_name": contact.name.middle_name,
        "created_at": contact.created_at,
        "updated_at": contact.updated_at,
        "created_by": contact.created_by.uuid,
        "updated_by": contact.updated_by.uuid,
    }


class SqlAlchemyContactRepository(CrmSessionRepository):
    """Реализует command/query CRM contact repositories через SQLAlchemy."""

    async def get(self, tenant_id, contact_id, *, for_update=False):
        """Читает один контакт текущего tenant."""
        table = ContactModel.__table__
        statement = select(table).where(table.c.id == contact_id.uuid)
        if for_update:
            statement = statement.with_for_update()
        result = await self.session.execute(
            statement.execution_options(**self.execution_options(tenant_id))
        )
        row = result.mappings().one_or_none()
        if row is None:
            raise ContactNotFoundError("Contact not found.")
        return contact_entity(row)

    async def add(self, tenant_id, contact):
        """Добавляет контакт в tenant-схему."""
        await self.session.execute(
            insert(ContactModel.__table__)
            .values(contact_values(contact))
            .execution_options(**self.execution_options(tenant_id))
        )

    async def save(self, tenant_id, contact):
        """Сохраняет изменяемые поля и update audit."""
        values = contact_values(contact)
        values.pop("id")
        values.pop("created_at")
        values.pop("created_by")
        result = await self.session.execute(
            update(ContactModel.__table__)
            .where(ContactModel.__table__.c.id == contact.id.uuid)
            .values(values)
            .execution_options(**self.execution_options(tenant_id))
        )
        if not result.rowcount:
            raise ContactNotFoundError("Contact not found.")

    async def delete(self, tenant_id, contact_id):
        """Физически удаляет контакт текущего tenant."""
        result = await self.session.execute(
            delete(ContactModel.__table__)
            .where(ContactModel.__table__.c.id == contact_id.uuid)
            .execution_options(**self.execution_options(tenant_id))
        )
        if not result.rowcount:
            raise ContactNotFoundError("Contact not found.")

    async def list(self, query: ListContactsQuery) -> ContactPageDTO:
        """Ищет контакты и возвращает offset-страницу со stable sort."""
        table = ContactModel.__table__
        clauses = []
        q = query.q.strip()
        if q:
            pattern = f"%{q}%"
            display_name = func.concat_ws(
                " ", table.c.last_name, table.c.first_name, table.c.middle_name
            )
            clauses.append(
                or_(
                    table.c.first_name.ilike(pattern),
                    table.c.last_name.ilike(pattern),
                    table.c.middle_name.ilike(pattern),
                    display_name.ilike(pattern),
                )
            )
        options = self.execution_options(query.tenant_id)
        count_statement = select(func.count()).select_from(table)
        list_statement = select(table)
        if clauses:
            count_statement = count_statement.where(*clauses)
            list_statement = list_statement.where(*clauses)
        total = int(
            await self.session.scalar(count_statement.execution_options(**options)) or 0
        )
        result = await self.session.execute(
            list_statement.order_by(
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
            items=tuple(contact_dto(contact_entity(row)) for row in result.mappings()),
            total=total,
            limit=query.limit,
            offset=query.offset,
        )


__all__ = ["SqlAlchemyContactRepository", "contact_entity", "contact_values"]
