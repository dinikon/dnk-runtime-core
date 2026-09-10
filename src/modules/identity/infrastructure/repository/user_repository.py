from __future__ import annotations

from sqlalchemy import Select, insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.identity.domain.user import (
    User,
    UserEmail,
    UserEmailIdVO,
    UserIdVO,
    UserRepositoryProtocol,
)
from src.modules.identity.infrastructure.persistence.user import UserModel
from src.modules.identity.infrastructure.persistence.user_email import UserEmailModel
from src.modules.shared import DomainError, EntityIdVO
from src.modules.shared.application.persistence.tenant_schema_naming import (
    TenantSchemaNaming,
)
from src.modules.shared.infrastructure.persistence.base import TENANT_SCHEMA_ALIAS


class SqlAlchemyUserRepository(UserRepositoryProtocol):
    """Хранит пользователей в схеме tenant, явно переданного каждой операции."""

    def __init__(self, session: AsyncSession, naming: TenantSchemaNaming) -> None:
        """Сохраняет UoW session и общую стратегию именования схем."""
        self._session = session
        self._naming = naming

    def _schema_map(self, tenant_id: EntityIdVO) -> dict[str, str]:
        return {TENANT_SCHEMA_ALIAS: self._naming.schema_name(tenant_id)}

    async def add(self, user: User, *, tenant_id: EntityIdVO) -> None:
        """Добавляет пользователя и emails в одной транзакции выбранного tenant."""
        if user.tenant_id != tenant_id:
            raise DomainError("User does not belong to the requested tenant.")
        schema_map = self._schema_map(tenant_id)
        # Core statements keep tenant selection out of the ORM identity map and
        # connection state, including when IDs coincide across tenant schemas.
        await self._session.execute(
            insert(UserModel.__table__)
            .values(
                id=user.id.uuid,
                status=user.status,
                user_type="user",
                last_name=user.last_name,
                first_name=user.first_name,
                middle_name=user.middle_name,
                avatar=user.avatar,
                interface_language=user.interface_language,
                interface_theme=user.interface_theme,
                timezone=user.timezone,
                last_active_at=user.last_active_at,
                last_login_ip=user.last_login_ip,
                initialized_at=user.initialized_at,
                created_at=user.created_at,
                updated_at=user.updated_at,
                # Preserve the previous ORM insert's server default for None.
                **(
                    {"last_login_at": user.last_login_at}
                    if user.last_login_at is not None
                    else {}
                ),
            )
            .execution_options(schema_translate_map=schema_map)
        )
        for email in user.emails:
            await self._session.execute(
                insert(UserEmailModel.__table__)
                .values(
                    id=email.id.uuid,
                    user_id=email.user_id.uuid,
                    email=email.email,
                    is_primary=email.is_primary,
                    is_verified=email.is_verified,
                    is_deleted=email.is_deleted,
                    created_at=email.created_at,
                    updated_at=email.updated_at,
                )
                .execution_options(schema_translate_map=schema_map)
            )

    async def get_by_id(
        self, user_id: UserIdVO, *, tenant_id: EntityIdVO
    ) -> User | None:
        """Читает пользователя и emails только из указанной tenant-схемы."""
        users = UserModel.__table__
        return await self._get_user(
            tenant_id, select(users).where(users.c.id == user_id.uuid)
        )

    async def get_by_tenant_and_primary_email(
        self,
        tenant_id: EntityIdVO,
        email: str,
    ) -> User | None:
        """Находит пользователя tenant по не удаленному primary email."""
        users, emails = UserModel.__table__, UserEmailModel.__table__
        return await self._get_user(
            tenant_id,
            select(users)
            .join(emails, emails.c.user_id == users.c.id)
            .where(emails.c.email == email)
            .where(emails.c.is_primary.is_(True))
            .where(emails.c.is_deleted.is_(False)),
        )

    async def _get_user(self, tenant_id: EntityIdVO, statement: Select) -> User | None:
        schema_map = self._schema_map(tenant_id)
        result = await self._session.execute(
            statement.execution_options(schema_translate_map=schema_map)
        )
        row = result.mappings().one_or_none()
        if row is None:
            return None
        emails = UserEmailModel.__table__
        result = await self._session.execute(
            select(emails)
            .where(emails.c.user_id == row["id"])
            .execution_options(schema_translate_map=schema_map)
        )
        return User(
            id=UserIdVO.from_value(row["id"]),
            tenant_id=tenant_id,
            status=row["status"],
            last_name=row["last_name"],
            first_name=row["first_name"],
            middle_name=row["middle_name"],
            avatar=row["avatar"],
            interface_language=row["interface_language"],
            interface_theme=row["interface_theme"],
            timezone=row["timezone"],
            last_login_at=row["last_login_at"],
            last_active_at=row["last_active_at"],
            last_login_ip=row["last_login_ip"],
            initialized_at=row["initialized_at"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            emails=[
                UserEmail(
                    id=UserEmailIdVO.from_value(email["id"]),
                    user_id=UserIdVO.from_value(email["user_id"]),
                    email=email["email"],
                    is_primary=email["is_primary"],
                    is_verified=email["is_verified"],
                    is_deleted=email["is_deleted"],
                    created_at=email["created_at"],
                    updated_at=email["updated_at"],
                )
                for email in result.mappings().all()
            ],
        )

    async def update_profile(self, user: User, *, tenant_id: EntityIdVO) -> None:
        """Сохраняет профиль только в схеме tenant пользователя."""
        if user.tenant_id != tenant_id:
            raise DomainError("User does not belong to the requested tenant.")
        users = UserModel.__table__
        await self._session.execute(
            update(users)
            .where(users.c.id == user.id.uuid)
            .values(
                last_name=user.last_name,
                first_name=user.first_name,
                middle_name=user.middle_name,
                interface_language=user.interface_language,
                interface_theme=user.interface_theme,
                timezone=user.timezone,
                updated_at=user.updated_at,
            )
            .execution_options(schema_translate_map=self._schema_map(tenant_id))
        )

    async def mark_email_verified(
        self, user_email_id: UserEmailIdVO, *, tenant_id: EntityIdVO
    ) -> None:
        """Подтверждает email только в указанной tenant-схеме."""
        emails = UserEmailModel.__table__
        await self._session.execute(
            update(emails)
            .where(emails.c.id == user_email_id.uuid)
            .values(is_verified=True)
            .execution_options(schema_translate_map=self._schema_map(tenant_id))
        )

    async def exists_by_tenant_and_email(
        self,
        tenant_id: EntityIdVO,
        email: str,
    ) -> bool:
        """Проверяет существование не удаленного email в tenant."""
        emails = UserEmailModel.__table__
        result = await self._session.execute(
            select(emails.c.id)
            .where(emails.c.email == email)
            .where(emails.c.is_deleted.is_(False))
            .limit(1)
            .execution_options(schema_translate_map=self._schema_map(tenant_id))
        )
        return result.scalar_one_or_none() is not None


__all__ = ["SqlAlchemyUserRepository"]
