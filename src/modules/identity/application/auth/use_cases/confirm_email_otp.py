from __future__ import annotations

from modules.shared.db.uow import UnitOfWorkProtocol
from src.modules.identity.application.auth.dto import (
    ConfirmEmailOtpCommandDTO,
    ConfirmEmailOtpResultDTO,
)
from src.modules.identity.application.auth.ports.repositories import (
    AuthUserRepositoryPort,
)
from src.modules.identity.application.auth.ports.tenant_context import (
    TenantContextReaderPort,
)
from src.modules.identity.application.auth.ports.token_store import (
    OtpChallengeStorePort,
    SessionRecord,
    SessionStorePort,
)
from src.modules.identity.application.auth.services.otp_service import (
    OtpServiceProtocol,
)
from src.modules.identity.application.auth.services.session_service import (
    SessionServiceProtocol,
)
from src.modules.identity.domain.errors import (
    InvalidOtpChallengeError,
    InvalidOtpCodeError,
    PrimaryUserEmailNotFoundError,
    UserLoginUnavailableError,
)
from src.modules.shared.http.host import normalize_host


class ConfirmEmailOtpUseCase:
    def __init__(
        self,
        uow: UnitOfWorkProtocol,
        tenant_context_reader: TenantContextReaderPort,
        users_repository: AuthUserRepositoryPort,
        otp_challenge_store: OtpChallengeStorePort,
        session_store: SessionStorePort,
        otp_service: OtpServiceProtocol,
        session_service: SessionServiceProtocol,
        session_ttl_seconds: int,
    ):
        self._uow = uow
        self._tenant_context_reader = tenant_context_reader
        self._users_repository = users_repository
        self._otp_challenge_store = otp_challenge_store
        self._session_store = session_store
        self._otp_service = otp_service
        self._session_service = session_service
        self._session_ttl_seconds = session_ttl_seconds

    async def execute(
        self,
        dto: ConfirmEmailOtpCommandDTO,
    ) -> ConfirmEmailOtpResultDTO:
        host = normalize_host(dto.host)
        email = dto.email.strip().lower()

        tenant_context = await self._tenant_context_reader.get_by_host(host)

        challenge = await self._otp_challenge_store.get_challenge(
            tenant_context.tenant_id,
            dto.token,
        )
        if challenge is None:
            raise InvalidOtpChallengeError()
        if (
            challenge.email != email
            or challenge.host != tenant_context.host
            or challenge.tenant_id != tenant_context.tenant_id
            or challenge.tenant_domain_id != tenant_context.tenant_domain_id
        ):
            raise InvalidOtpChallengeError()
        if not self._otp_service.verify_code(
            code=dto.code,
            code_hash=challenge.code_hash,
        ):
            raise InvalidOtpCodeError()

        user = await self._users_repository.get_by_tenant_and_primary_email(
            tenant_context.tenant_id,
            email,
        )
        if user is None:
            raise PrimaryUserEmailNotFoundError(email)
        if not user.can_login():
            raise UserLoginUnavailableError()

        primary_email = user.get_primary_email(email)
        if primary_email is None:
            raise PrimaryUserEmailNotFoundError(email)

        generated_session = self._session_service.generate(
            ttl_seconds=self._session_ttl_seconds
        )

        try:
            await self._session_store.create_session(
                SessionRecord(
                    token=generated_session.token,
                    session_id=generated_session.session_id,
                    user_id=user.id,
                    tenant_id=tenant_context.tenant_id,
                    tenant_domain_id=tenant_context.tenant_domain_id,
                    host=tenant_context.host,
                    issued_at=generated_session.issued_at,
                    expires_at=generated_session.expires_at,
                ),
                ttl_seconds=self._session_ttl_seconds,
            )
            await self._otp_challenge_store.invalidate_challenge(
                tenant_context.tenant_id,
                dto.token,
            )
            if not primary_email.is_verified:
                user.mark_email_verified(primary_email.id)
                await self._users_repository.mark_email_verified(primary_email.id)
            await self._uow.commit()
        except Exception:
            await self._uow.rollback()
            raise

        return ConfirmEmailOtpResultDTO(
            ok=True,
            user_id=user.id,
            tenant_id=tenant_context.tenant_id,
            session_token=generated_session.token,
            expires_in=self._session_ttl_seconds,
        )
