from uuid import UUID
from src.modules.identity.domain.access.error import IdentityAccessError
from src.modules.identity.domain.user.value_object.user_id import UserIdVO
from src.modules.shared import EntityIdVO
from src.modules.identity.domain.user.repository import UserRepositoryProtocol
from src.modules.identity.application.access.port.repository import (
    AccessRepositoryProtocol,
)
from src.modules.identity.application.cloud.port.cloud import AccessProjectionWriterPort
from src.modules.shared.application.persistence.unit_of_work import UnitOfWorkProtocol
from src.modules.identity.application.auth.service.session_authentication import (
    SessionAuthenticationService,
)
from src.modules.identity.application.access.command.change_user_access.command import (
    ChangeUserAccessCommand,
)
from src.modules.identity.application.access.command.change_user_access.dto import (
    ChangeUserAccessResultDTO,
)


class ChangeUserAccessHandler:

    def __init__(
        self,
        *,
        access: AccessRepositoryProtocol,
        authentication: SessionAuthenticationService,
        projections: AccessProjectionWriterPort,
        uow: UnitOfWorkProtocol,
        users: UserRepositoryProtocol,
    ) -> None:
        self.access = access
        self.authentication = authentication
        self.projections = projections
        self.uow = uow
        self.users = users

    async def execute(
        self, request: ChangeUserAccessCommand
    ) -> ChangeUserAccessResultDTO:
        host = request.host
        session_token = request.session_token
        user_id = request.user_id
        role = request.role
        status = request.status
        context, _, _ = await self.authentication.principal(
            host, session_token, admin=True, locked=True
        )
        user = await self.users.get_by_id(
            UserIdVO.from_value(user_id),
            tenant_id=EntityIdVO.from_value(context.tenant_id),
        )
        if user is None:
            raise IdentityAccessError("User not found.", 404)
        next_role, next_status = (role or user.role, status or user.status)
        if next_role not in {"admin", "member"} or next_status not in {
            "active",
            "revoked",
        }:
            raise IdentityAccessError("Invalid role or status.", 422)
        if (
            user.role == "admin"
            and user.can_login()
            and (next_role != "admin" or next_status != "active")
            and (await self.access.active_admin_count(context.tenant_id) <= 1)
        ):
            raise IdentityAccessError(
                "The last active administrator cannot be disabled or demoted.", 409
            )
        if (next_role, next_status) != (user.role, user.status):
            await self.access.change_access(
                context.tenant_id, user.id.uuid, next_role, next_status
            )
            binding = await self.access.identity_for_user(
                context.tenant_id, user.id.uuid
            )
            if binding:
                await self.projections.set_available(
                    context.tenant_id,
                    UUID(binding.subject),
                    next_status == "active",
                    next_role,
                )
        await self.uow.commit()
        return ChangeUserAccessResultDTO(ok=True)
