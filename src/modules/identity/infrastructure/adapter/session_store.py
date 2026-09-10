from __future__ import annotations

from datetime import datetime
from uuid import UUID

from src.modules.identity.application.ports import SessionRecord, SessionStorePort
from src.modules.shared.application.tokens import TokenManager


class TokenManagerBackedSessionStore(SessionStorePort):
    """SessionStore поверх shared TokenManager."""

    def __init__(self, token_manager: TokenManager):
        """Инициализирует store token manager-ом."""
        self._token_manager = token_manager

    async def create_session(self, session: SessionRecord, ttl_seconds: int) -> None:
        """Сохраняет session record в token manager namespace tenant."""
        await self._token_manager.set_token(
            prefix="session",
            suffix=str(session.tenant_id),
            token=session.token,
            body={
                "token": session.token,
                "session_id": session.session_id,
                "user_id": session.user_id,
                "tenant_id": session.tenant_id,
                "tenant_domain_id": session.tenant_domain_id,
                "host": session.host,
                "issued_at": session.issued_at,
                "expires_at": session.expires_at,
            },
            ttl=ttl_seconds,
        )

    async def get_session(self, tenant_id: UUID, token: str) -> SessionRecord | None:
        """Читает session record из token manager и восстанавливает dataclass."""
        body = await self._token_manager.get_token(
            prefix="session",
            suffix=str(tenant_id),
            token=token,
        )
        if body is None:
            return None
        return SessionRecord(
            token=_required_str(body, "token"),
            session_id=_required_str(body, "session_id"),
            user_id=_required_uuid(body, "user_id"),
            tenant_id=_required_uuid(body, "tenant_id"),
            tenant_domain_id=_required_uuid(body, "tenant_domain_id"),
            host=_required_str(body, "host"),
            issued_at=_required_datetime(body, "issued_at"),
            expires_at=_required_datetime(body, "expires_at"),
        )

    async def invalidate_session(self, tenant_id: UUID, token: str) -> None:
        """Удаляет session record из token manager."""
        await self._token_manager.invalidate(
            prefix="session",
            suffix=str(tenant_id),
            token=token,
        )


def _required_str(body: dict[str, object], key: str) -> str:
    """Достает обязательное string-значение из token body."""
    value = body[key]
    assert isinstance(value, str)
    return value


def _required_uuid(body: dict[str, object], key: str) -> UUID:
    """Достает обязательный UUID из token body."""
    value = body[key]
    if isinstance(value, UUID):
        return value
    assert isinstance(value, str)
    return UUID(value)


def _required_datetime(body: dict[str, object], key: str) -> datetime:
    """Достает обязательный datetime из token body."""
    value = body[key]
    assert isinstance(value, datetime)
    return value


__all__ = ["TokenManagerBackedSessionStore"]
