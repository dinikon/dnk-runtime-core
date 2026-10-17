from sqlalchemy import Select, insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from src.modules.identity.domain.user.aggregate import User
from src.modules.identity.domain.user.value_object.user_id import UserIdVO
from src.modules.identity.domain.user.value_object.user_email_id import UserEmailIdVO
from src.modules.identity.domain.user.repository import UserRepositoryProtocol
from src.modules.identity.infrastructure.persistence.models.user import UserModel
from src.modules.identity.infrastructure.persistence.models.user_email import (
    UserEmailModel,
)
from src.modules.identity.infrastructure.user.persistence.mapper import UserMapper
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.shared.domain.domain_error import DomainError
from src.modules.tenancy.application.tenant.tenant_schema_naming import (
    TenantSchemaNaming,
)
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_connection import (
    require_tenant_schema,
)


class SqlAlchemyUserRepository(UserRepositoryProtocol):
    """Хранит агрегат на внешнем UoW, схема которого уже привязана к одному Tenant."""

    def __init__(self, session: AsyncSession, naming: TenantSchemaNaming) -> None:
        """Принимает общую сессию и правило проверки готовой привязки схемы."""
        self._session = session
        self._naming = naming

    async def _require_tenant(self, tenant_id: EntityIdVO) -> None:
        """Проверяет доверенный tenant-контекст, не выбирая схему для выражения."""
        await require_tenant_schema(
            await self._session.connection(), tenant_id.uuid, self._naming
        )

    async def add(self, user: User, *, tenant_id: EntityIdVO) -> None:
        """Записывает пользователя и его emails атомарно без самостоятельного commit."""
        if user.tenant_id != tenant_id:
            raise DomainError("User does not belong to the requested tenant.")
        await self._require_tenant(tenant_id)
        await self._session.execute(
            insert(UserModel.__table__).values(UserMapper.to_insert_values(user))
        )
        for email in user.emails:
            await self._session.execute(
                insert(UserEmailModel.__table__).values(
                    UserMapper.to_email_insert_values(email)
                )
            )

    async def get_by_id(
        self, user_id: UserIdVO, *, tenant_id: EntityIdVO, for_update: bool = False
    ) -> User | None:
        """Восстанавливает агрегат; изменение профиля запрашивает блокировку строки."""
        users = UserModel.__table__
        statement = select(users).where(users.c.id == user_id.uuid)
        if for_update:
            statement = statement.with_for_update()
        return await self._get_user(tenant_id, statement)

    async def get_by_tenant_and_primary_email(
        self, tenant_id: EntityIdVO, email: str
    ) -> User | None:
        """Находит пользователя по его активному primary email в привязанной схеме."""
        users, emails = UserModel.__table__, UserEmailModel.__table__
        return await self._get_user(
            tenant_id,
            select(users)
            .join(emails, emails.c.user_id == users.c.id)
            .where(
                emails.c.email == email,
                emails.c.is_primary.is_(True),
                emails.c.is_deleted.is_(False),
            ),
        )

    async def _get_user(self, tenant_id: EntityIdVO, statement: Select) -> User | None:
        """Читает строки агрегата и передаёт восстановление отдельному mapper."""
        await self._require_tenant(tenant_id)
        row = (await self._session.execute(statement)).mappings().one_or_none()
        if row is None:
            return None
        emails = UserEmailModel.__table__
        result = await self._session.execute(
            select(emails).where(emails.c.user_id == row["id"]).order_by(emails.c.id)
        )
        return UserMapper.to_domain(row, result.mappings().all(), tenant_id)

    async def update_profile(self, user: User, *, tenant_id: EntityIdVO) -> None:
        """Сохраняет профиль агрегата в общей транзакции указанного Tenant."""
        if user.tenant_id != tenant_id:
            raise DomainError("User does not belong to the requested tenant.")
        await self._require_tenant(tenant_id)
        users = UserModel.__table__
        await self._session.execute(
            update(users)
            .where(users.c.id == user.id.uuid)
            .values(UserMapper.to_profile_update_values(user))
        )

    async def mark_email_verified(
        self, user_email_id: UserEmailIdVO, *, tenant_id: EntityIdVO
    ) -> None:
        """Подтверждает email в заранее выбранной схеме внешнего UoW."""
        await self._require_tenant(tenant_id)
        emails = UserEmailModel.__table__
        await self._session.execute(
            update(emails)
            .where(emails.c.id == user_email_id.uuid)
            .values(is_verified=True)
        )

    async def exists_by_tenant_and_email(
        self, tenant_id: EntityIdVO, email: str
    ) -> bool:
        """Проверяет наличие не удалённого email без смены tenant-схемы."""
        await self._require_tenant(tenant_id)
        emails = UserEmailModel.__table__
        result = await self._session.execute(
            select(emails.c.id)
            .where(emails.c.email == email, emails.c.is_deleted.is_(False))
            .limit(1)
        )
        return result.scalar_one_or_none() is not None
