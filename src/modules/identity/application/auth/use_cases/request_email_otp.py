from __future__ import annotations

from src.modules.identity.application.auth.dto import (
    RequestEmailOtpCommandDTO,
    RequestEmailOtpResultDTO,
)
from src.modules.identity.application.auth.ports.email_sender import EmailSenderPort
from src.modules.identity.application.auth.ports.repositories import (
    AuthUserRepositoryPort,
)
from src.modules.identity.application.auth.ports.tenant_context import (
    TenantContextReaderPort,
)
from src.modules.identity.application.auth.ports.token_store import (
    OtpChallenge,
    OtpChallengeStorePort,
)
from src.modules.identity.application.auth.services.otp_service import (
    OtpServiceProtocol,
)
from src.modules.identity.domain.errors import (
    PrimaryUserEmailNotFoundError,
    UserLoginUnavailableError,
)
from src.modules.shared.http.host import normalize_host


class RequestEmailOtpUseCase:
    def __init__(
        self,
        tenant_context_reader: TenantContextReaderPort,
        users_repository: AuthUserRepositoryPort,
        otp_challenge_store: OtpChallengeStorePort,
        otp_service: OtpServiceProtocol,
        email_sender: EmailSenderPort,
        otp_ttl_seconds: int,
    ):
        self._tenant_context_reader = tenant_context_reader
        self._users_repository = users_repository
        self._otp_challenge_store = otp_challenge_store
        self._otp_service = otp_service
        self._email_sender = email_sender
        self._otp_ttl_seconds = otp_ttl_seconds

    async def execute(
        self,
        dto: RequestEmailOtpCommandDTO,
    ) -> RequestEmailOtpResultDTO:
        host = normalize_host(dto.host)
        email = dto.email.strip().lower()

        tenant_context = await self._tenant_context_reader.get_by_host(host)

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

        generated = self._otp_service.generate()
        await self._otp_challenge_store.create_challenge(
            OtpChallenge(
                token=generated.token,
                email=primary_email.email,
                tenant_id=tenant_context.tenant_id,
                tenant_domain_id=tenant_context.tenant_domain_id,
                host=tenant_context.host,
                code_hash=generated.code_hash,
                created_at=generated.created_at,
            ),
            ttl_seconds=self._otp_ttl_seconds,
        )
        print(generated.code)
        await self._email_sender.send_login_code(primary_email.email, generated.code)

        return RequestEmailOtpResultDTO(
            token=generated.token,
            expires_in=self._otp_ttl_seconds,
        )
