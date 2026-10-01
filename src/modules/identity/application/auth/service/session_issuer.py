from src.modules.identity.domain.user.entity import User
from src.modules.identity.application.auth.port.tenant_context_reader import (
    TenantRequestContext,
)
from src.modules.identity.application.auth.port.session_store import SessionRecord
from src.modules.identity.application.auth.port.session_store import SessionStorePort
from src.modules.identity.application.auth.service.session_service import (
    SessionServiceProtocol,
)
from src.config.feature.identity.auth_config import IdentityAuthSettings


class SessionIssuer:

    def __init__(
        self,
        *,
        session_service: SessionServiceProtocol,
        sessions: SessionStorePort,
        settings: IdentityAuthSettings,
    ) -> None:
        self.session_service = session_service
        self.sessions = sessions
        self.settings = settings

    async def issue_session(
        self, context: TenantRequestContext, user: User
    ) -> SessionRecord:
        generated = self.session_service.generate(
            ttl_seconds=self.settings.session_ttl_seconds
        )
        record = SessionRecord(
            token=generated.token,
            session_id=generated.session_id,
            user_id=user.id.uuid,
            tenant_id=context.tenant_id,
            tenant_domain_id=context.tenant_domain_id,
            host=context.host,
            issued_at=generated.issued_at,
            expires_at=generated.expires_at,
            session_epoch=user.session_epoch,
        )
        await self.sessions.create_session(record, self.settings.session_ttl_seconds)
        return record
