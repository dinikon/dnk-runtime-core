from __future__ import annotations

from typing import Sequence
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.identity.application.provisioning.ports.repositories import (
    UserRepositoryProtocol,
)
from src.modules.identity.domain.entities import User, UserEmail
from src.modules.identity.infrastructure.persistence.user import UserModel
from src.modules.identity.infrastructure.persistence.user_email import UserEmailModel


class SqlAlchemyUserRepository(UserRepositoryProtocol):
    def __init__(self, session: AsyncSession):
        self._session = session

    async def add(self, user: User) -> None:
        self._session.add(
            UserModel(
                id=user.id,
                tenant_id=user.tenant_id,
                status=user.status,
                last_name=user.last_name,
                first_name=user.first_name,
                middle_name=user.middle_name,
                avatar=user.avatar,
                interface__language=user.interface_language,
                interface_theme=user.interface_theme,
                timezone=user.timezone,
                last_login_at=user.last_login_at,
                last_active_at=user.last_active_at,
                last_login_ip=user.last_login_ip,
                initialized_at=user.initialized_at,
                created_at=user.created_at,
                updated_at=user.updated_at,
            )
        )
        for email in user.emails:
            self._session.add(
                UserEmailModel(
                    id=email.id,
                    user_id=email.user_id,
                    email=email.email,
                    is_primary=email.is_primary,
                    is_verified=email.is_verified,
                    is_deleted=email.is_deleted,
                    created_at=email.created_at,
                    updated_at=email.updated_at,
                )
            )
        await self._session.flush()

    async def get_by_id(self, user_id: UUID) -> User | None:
        user_model = await self._session.scalar(
            select(UserModel).where(UserModel.id == str(user_id))
        )
        if user_model is None:
            return None

        email_models = (
            await self._session.scalars(
                select(UserEmailModel).where(UserEmailModel.user_id == str(user_id))
            )
        ).all()
        return self._map_user(user_model, email_models)

    async def get_by_tenant_and_primary_email(
        self,
        tenant_id: UUID,
        email: str,
    ) -> User | None:
        user_model = await self._session.scalar(
            select(UserModel)
            .join(UserEmailModel, UserEmailModel.user_id == UserModel.id)
            .where(UserModel.tenant_id == str(tenant_id))
            .where(UserEmailModel.email == email)
            .where(UserEmailModel.is_primary.is_(True))
            .where(UserEmailModel.is_deleted.is_(False))
            .limit(1)
        )
        if user_model is None:
            return None

        email_models = (
            await self._session.scalars(
                select(UserEmailModel).where(UserEmailModel.user_id == user_model.id)
            )
        ).all()
        return self._map_user(user_model, email_models)

    async def update_profile(self, user: User) -> None:
        await self._session.execute(
            update(UserModel)
            .where(UserModel.id == str(user.id))
            .values(
                last_name=user.last_name,
                first_name=user.first_name,
                middle_name=user.middle_name,
                interface__language=user.interface_language,
                interface_theme=user.interface_theme,
                timezone=user.timezone,
                updated_at=user.updated_at,
            )
        )
        await self._session.flush()

    async def mark_email_verified(self, user_email_id: UUID) -> None:
        await self._session.execute(
            update(UserEmailModel)
            .where(UserEmailModel.id == str(user_email_id))
            .values(is_verified=True)
        )
        await self._session.flush()

    async def exists_by_tenant_and_email(
        self,
        tenant_id: UUID,
        email: str,
    ) -> bool:
        email_id = await self._session.scalar(
            select(UserEmailModel.id)
            .join(UserModel, UserModel.id == UserEmailModel.user_id)
            .where(UserModel.tenant_id == str(tenant_id))
            .where(UserEmailModel.email == email)
            .where(UserEmailModel.is_deleted.is_(False))
            .limit(1)
        )
        return email_id is not None

    @staticmethod
    def _map_user(
        user_model: UserModel, email_models: Sequence[UserEmailModel]
    ) -> User:
        return User(
            id=_to_uuid(user_model.id),
            tenant_id=_to_uuid(user_model.tenant_id),
            status=user_model.status,
            last_name=user_model.last_name,
            first_name=user_model.first_name,
            middle_name=user_model.middle_name,
            avatar=user_model.avatar,
            interface_language=user_model.interface__language,
            interface_theme=user_model.interface_theme,
            timezone=user_model.timezone,
            last_login_at=user_model.last_login_at,
            last_active_at=user_model.last_active_at,
            last_login_ip=user_model.last_login_ip,
            initialized_at=user_model.initialized_at,
            created_at=user_model.created_at,
            updated_at=user_model.updated_at,
            emails=[
                SqlAlchemyUserRepository._map_email(email_model)
                for email_model in email_models
            ],
        )

    @staticmethod
    def _map_email(model: UserEmailModel) -> UserEmail:
        return UserEmail(
            id=_to_uuid(model.id),
            user_id=_to_uuid(model.user_id),
            email=model.email,
            is_primary=model.is_primary,
            is_verified=model.is_verified,
            is_deleted=model.is_deleted,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )


def _to_uuid(value: UUID | str) -> UUID:
    if isinstance(value, UUID):
        return value
    return UUID(value)
