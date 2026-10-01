from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.crm.application.contact.query.get_contact.dto import ContactDetailsDTO
from src.modules.crm.domain.contact.value_object.identifier import ContactIdVO
from src.modules.crm.infrastructure.contact.persistence.query_mapper import (
    ContactQueryMapper,
)
from src.modules.crm.infrastructure.persistence.models.contact import ContactModel
from src.modules.tenancy.application.tenant.tenant_schema_naming import (
    TenantSchemaNaming,
)
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_base import (
    TENANT_SCHEMA_ALIAS,
)


class SqlAlchemyContactQueryRepository:
    """Читает проекцию контакта одним SELECT в схеме текущего вызова."""

    def __init__(self, session: AsyncSession, naming: TenantSchemaNaming) -> None:
        """Получает внешнюю сессию и стратегию имён tenant-схем."""
        self._session = session
        self._naming = naming

    async def get_details(
        self,
        *,
        tenant_id: EntityIdVO,
        contact_id: ContactIdVO,
    ) -> ContactDetailsDTO | None:
        """Возвращает сохранённые поля без блокировки и загрузки агрегата."""
        result = await self._session.execute(
            select(
                ContactModel.id.label("id"),
                ContactModel.first_name.label("first_name"),
                ContactModel.last_name.label("last_name"),
                ContactModel.middle_name.label("middle_name"),
                ContactModel.created_at.label("created_at"),
                ContactModel.updated_at.label("updated_at"),
                ContactModel.created_by.label("created_by"),
                ContactModel.updated_by.label("updated_by"),
            )
            .where(ContactModel.id == contact_id.uuid)
            .execution_options(
                schema_translate_map={
                    TENANT_SCHEMA_ALIAS: self._naming.schema_name(tenant_id)
                }
            )
        )
        row = result.mappings().one_or_none()
        return None if row is None else ContactQueryMapper.to_details(row)
