from src.modules.crm.domain.company.value_object import CompanyIdVO
from datetime import datetime

from sqlalchemy import delete, insert, select, update

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
from src.modules.crm.infrastructure.persistence.models import (
    ContactModel,
    ContactCompanyModel,
)


def contact_entity(row, company_ids=()) -> Contact:
    """Явно мапит persistence row в Contact aggregate."""
    return Contact(
        id=identifier(row["id"], ContactIdVO),
        _company_ids=frozenset(company_ids),
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
    """Реализует command CRM contact repository через SQLAlchemy."""

    def __init__(self, session, naming):
        super().__init__(session, naming)
        self._original_links = {}

    async def _load_links(self, tenant_id, contact_id):
        table = ContactCompanyModel.__table__
        result = await self.session.scalars(
            select(table.c.company_id)
            .where(table.c.contact_id == contact_id.uuid)
            .execution_options(**self.execution_options(tenant_id))
        )
        return frozenset(CompanyIdVO.from_value(value) for value in result)

    async def get_many(self, tenant_id, contact_ids, *, for_update=False):
        # All commands acquire Contact locks before Company locks, in UUID order.
        contacts = []
        for contact_id in sorted(set(contact_ids), key=lambda value: value.uuid):
            try:
                contacts.append(
                    await self.get(tenant_id, contact_id, for_update=for_update)
                )
            except ContactNotFoundError:
                continue
        return tuple(contacts)

    async def _save_links(self, tenant_id, contact):
        key = (tenant_id, contact.id)
        previous = self._original_links.get(key)
        if previous is None:
            previous = await self._load_links(tenant_id, contact.id)
        removed = previous - contact.company_ids
        added = contact.company_ids - previous
        table = ContactCompanyModel.__table__
        options = self.execution_options(tenant_id)
        if removed:
            await self.session.execute(
                delete(table)
                .where(
                    table.c.contact_id == contact.id.uuid,
                    table.c.company_id.in_([value.uuid for value in removed]),
                )
                .execution_options(**options)
            )
        if added:
            await self.session.execute(
                insert(table).execution_options(**options),
                [
                    {"contact_id": contact.id.uuid, "company_id": value.uuid}
                    for value in sorted(added, key=lambda value: value.uuid)
                ],
            )
        self._original_links[key] = contact.company_ids

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
        links = await self._load_links(tenant_id, contact_id)
        self._original_links[(tenant_id, contact_id)] = links
        return contact_entity(row, links)

    async def add(self, tenant_id, contact):
        """Добавляет контакт в tenant-схему."""
        await self.session.execute(
            insert(ContactModel.__table__)
            .values(contact_values(contact))
            .execution_options(**self.execution_options(tenant_id))
        )

        self._original_links[(tenant_id, contact.id)] = frozenset()
        await self._save_links(tenant_id, contact)

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

        await self._save_links(tenant_id, contact)

    async def delete(self, tenant_id, contact_id):
        """Физически удаляет контакт текущего tenant."""
        result = await self.session.execute(
            delete(ContactModel.__table__)
            .where(ContactModel.__table__.c.id == contact_id.uuid)
            .execution_options(**self.execution_options(tenant_id))
        )
        if not result.rowcount:
            raise ContactNotFoundError("Contact not found.")


__all__ = ["SqlAlchemyContactRepository", "contact_entity", "contact_values"]
