from sqlalchemy import insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.crm.domain.contact.aggregate import Contact
from src.modules.crm.infrastructure.contact.persistence.mapper import ContactMapper
from src.modules.crm.infrastructure.persistence.models.contact import ContactModel
from src.modules.tenancy.application.tenant.tenant_schema_naming import (
    TenantSchemaNaming,
)
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_base import (
    TENANT_SCHEMA_ALIAS,
)


class SqlAlchemyContactRepository:
    """Сохраняет контакты в tenant-схеме на сессии внешнего UoW."""

    def __init__(self, session: AsyncSession, naming: TenantSchemaNaming) -> None:
        """Получает сессию и стратегию имён схем без фиксации текущего tenant."""
        self._session = session
        self._naming = naming

    async def add(self, tenant_id: EntityIdVO, contact: Contact) -> None:
        """Добавляет агрегат в схему текущего вызова без commit/rollback."""
        await self._session.execute(
            insert(ContactModel)
            .values(ContactMapper.to_insert_values(contact))
            .execution_options(
                schema_translate_map={
                    TENANT_SCHEMA_ALIAS: self._naming.schema_name(tenant_id)
                }
            )
        )
