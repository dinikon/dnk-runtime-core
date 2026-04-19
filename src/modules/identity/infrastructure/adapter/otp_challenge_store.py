from __future__ import annotations

from datetime import datetime
from uuid import UUID

from src.modules.identity.application.ports import OtpChallenge, OtpChallengeStorePort
from src.modules.shared.kernel.tokens import TokenManager


class TokenManagerBackedOtpChallengeStore(OtpChallengeStorePort):
    """OtpChallengeStore поверх shared TokenManager."""

    def __init__(self, token_manager: TokenManager):
        """Инициализирует store token manager-ом."""
        self._token_manager = token_manager

    async def create_challenge(self, challenge: OtpChallenge, ttl_seconds: int) -> None:
        """Сохраняет OTP challenge в token manager namespace tenant."""
        await self._token_manager.set_token(
            prefix="otp_login",
            suffix=str(challenge.tenant_id),
            token=challenge.token,
            body={
                "token": challenge.token,
                "email": challenge.email,
                "tenant_id": challenge.tenant_id,
                "tenant_domain_id": challenge.tenant_domain_id,
                "host": challenge.host,
                "code_hash": challenge.code_hash,
                "created_at": challenge.created_at,
            },
            ttl=ttl_seconds,
        )

    async def get_challenge(self, tenant_id: UUID, token: str) -> OtpChallenge | None:
        """Читает OTP challenge из token manager и восстанавливает dataclass."""
        body = await self._token_manager.get_token(
            prefix="otp_login",
            suffix=str(tenant_id),
            token=token,
        )
        if body is None:
            return None
        return OtpChallenge(
            token=_required_str(body, "token"),
            email=_required_str(body, "email"),
            tenant_id=_required_uuid(body, "tenant_id"),
            tenant_domain_id=_required_uuid(body, "tenant_domain_id"),
            host=_required_str(body, "host"),
            code_hash=_required_str(body, "code_hash"),
            created_at=_required_datetime(body, "created_at"),
        )

    async def invalidate_challenge(self, tenant_id: UUID, token: str) -> None:
        """Удаляет OTP challenge из token manager."""
        await self._token_manager.invalidate(
            prefix="otp_login",
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


__all__ = ["TokenManagerBackedOtpChallengeStore"]
