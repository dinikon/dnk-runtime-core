from src.modules.identity.application.email.system_email_kind import SystemEmailKind
from src.modules.identity.application.auth.port.tenant_context_reader import (
    TenantContextReaderPort,
)
from src.modules.identity.application.auth.service.otp_service import OtpServiceProtocol
from src.modules.identity.application.email.email_service_port import EmailServicePort
from src.modules.shared.application.tokens.token_manager import TokenManager
from src.config.feature.identity.auth_config import IdentityAuthSettings
from src.modules.identity.application.invitation.service.validator import (
    InvitationValidator,
)
from src.modules.identity.application.invitation.command.request_invitation_otp.command import (
    RequestInvitationOtpCommand,
)
from src.modules.identity.application.invitation.command.request_invitation_otp.dto import (
    RequestInvitationOtpResultDTO,
)


class RequestInvitationOtpHandler:

    def __init__(
        self,
        *,
        email: EmailServicePort,
        invitations: InvitationValidator,
        otp: OtpServiceProtocol,
        settings: IdentityAuthSettings,
        tenant_reader: TenantContextReaderPort,
        tokens: TokenManager,
    ) -> None:
        self.email = email
        self.invitations = invitations
        self.otp = otp
        self.settings = settings
        self.tenant_reader = tenant_reader
        self.tokens = tokens

    async def execute(
        self, request: RequestInvitationOtpCommand
    ) -> RequestInvitationOtpResultDTO:
        host = request.host
        invitation_token = request.invitation_token
        context = await self.tenant_reader.get_by_host(host)
        invitation = await self.invitations.valid_invitation(
            context.tenant_id, invitation_token
        )
        generated = self.otp.generate()
        await self.tokens.set_token(
            prefix="invitation_otp",
            suffix=str(context.tenant_id),
            token=generated.token,
            body={
                "purpose": "invitation",
                "invitation_id": str(invitation.id),
                "host": context.host,
                "domain_id": str(context.tenant_domain_id),
                "email": invitation.email,
                "hash": generated.code_hash,
            },
            ttl=self.settings.otp_token_ttl_seconds,
        )
        await self.email.send(
            SystemEmailKind.SEND_OTP_CODE,
            invitation.email,
            {"otp_code": generated.code},
        )
        return RequestInvitationOtpResultDTO(
            token=generated.token,
            expires_in=self.settings.otp_token_ttl_seconds,
            code=generated.code,
        )
