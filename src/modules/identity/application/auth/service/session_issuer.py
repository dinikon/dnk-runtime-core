from src.modules.identity.domain.user.aggregate import User
from src.modules.identity.application.auth.port.tenant_context_reader import (
    TenantRequestContext,
)
from src.modules.identity.application.auth.port.session_store import SessionRecord
from src.modules.identity.application.auth.port.session_store import SessionStorePort
from src.modules.identity.application.auth.service.session_service import (
    SessionServiceProtocol,
)


class SessionIssuer:
    """Создаёт tenant-session с текущей ролью и epoch пользователя."""

    def __init__(
        self,
        *,
        session_service: SessionServiceProtocol,
        sessions: SessionStorePort,
        session_ttl_seconds: int,
    ) -> None:
        """Принимает генератор, хранилище sessions и срок действия в секундах."""
        self.session_service = session_service
        self.sessions = sessions
        self._session_ttl_seconds = session_ttl_seconds

    async def issue_session(
        self, context: TenantRequestContext, user: User
    ) -> SessionRecord:
        """Генерирует запись session и сохраняет её через порт хранилища."""
        generated = self.session_service.generate(ttl_seconds=self._session_ttl_seconds)
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
        await self.sessions.create_session(record, self._session_ttl_seconds)
        return record
