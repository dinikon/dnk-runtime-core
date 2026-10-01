from __future__ import annotations
from src.modules.identity.application.user.command.create_tenant_admin.dto import (
    CreatedTenantAdmin,
)
from src.modules.identity.domain.user.entity import User
from src.modules.identity.domain.user.error import UserEmailAlreadyExistsError
from src.modules.identity.domain.user.repository import UserRepositoryProtocol
from src.modules.identity.application.user.command.create_tenant_admin.command import (
    CreateTenantAdminCommand,
)


class CreateTenantAdminHandler:

    def __init__(self, users_repository: UserRepositoryProtocol):
        self._users_repository = users_repository

    async def execute(self, command: CreateTenantAdminCommand) -> CreatedTenantAdmin:
        tenant_id = command.tenant_id
        first_name = command.first_name
        last_name = command.last_name
        email = command.email
        "Создает tenant admin и primary email после проверки уникальности email."
        normalized_first_name = first_name.strip()
        normalized_last_name = last_name.strip()
        normalized_email = email.strip().lower()
        if await self._users_repository.exists_by_tenant_and_email(
            tenant_id=tenant_id, email=normalized_email
        ):
            raise UserEmailAlreadyExistsError(normalized_email)
        user = User.create_tenant_admin(
            tenant_id=tenant_id,
            first_name=normalized_first_name,
            last_name=normalized_last_name,
        )
        primary_email = user.add_email(normalized_email, is_primary=True)
        await self._users_repository.add(user, tenant_id=tenant_id)
        return CreatedTenantAdmin(
            user_id=user.id.uuid,
            user_email_id=primary_email.id.uuid,
            user_status=user.status,
        )
