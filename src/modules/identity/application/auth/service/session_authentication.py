from src.modules.identity.domain.user.entity import User
from src.modules.identity.application.auth.port.tenant_context_reader import (
    TenantRequestContext,
)
from src.modules.identity.application.auth.port.session_store import SessionRecord
from src.modules.identity.domain.access.error import IdentityAccessError
from src.modules.identity.domain.user.value_object.user_id import UserIdVO
from src.modules.shared import EntityIdVO
from src.modules.identity.domain.user.repository import UserRepositoryProtocol
from src.modules.identity.application.auth.port.session_store import SessionStorePort
from src.modules.identity.application.auth.port.tenant_context_reader import (
    TenantContextReaderPort,
)
from src.modules.identity.application.access.port.repository import (
    AccessRepositoryProtocol,
)


class SessionAuthenticationService:

    def __init__(
        self,
        *,
        access: AccessRepositoryProtocol,
        sessions: SessionStorePort,
        tenant_reader: TenantContextReaderPort,
        users: UserRepositoryProtocol,
    ) -> None:
        self.access = access
        self.sessions = sessions
        self.tenant_reader = tenant_reader
        self.users = users

    async def principal(
        self,
        host: str,
        session_token: str | None,
        *,
        admin: bool = False,
        locked: bool = False,
    ) -> tuple[TenantRequestContext, User, SessionRecord]:
        context = await self.tenant_reader.get_by_host(host)
        if locked:
            await self.access.lock(context.tenant_id)
        session = (
            await self.sessions.get_session(context.tenant_id, session_token)
            if session_token
            else None
        )
        if session is None or (
            session.host,
            session.tenant_id,
            session.tenant_domain_id,
        ) != (context.host, context.tenant_id, context.tenant_domain_id):
            raise IdentityAccessError("Authentication required.", 401)
        user = await self.users.get_by_id(
            UserIdVO.from_value(session.user_id),
            tenant_id=EntityIdVO.from_value(context.tenant_id),
        )
        if (
            user is None
            or not user.can_login()
            or user.session_epoch != session.session_epoch
        ):
            raise IdentityAccessError("Authentication required.", 401)
        if admin and user.role != "admin":
            raise IdentityAccessError("Administrator access required.", 403)
        return (context, user, session)
