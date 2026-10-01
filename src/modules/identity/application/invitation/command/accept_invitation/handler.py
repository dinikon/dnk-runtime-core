from src.modules.identity.domain.access.error import IdentityAccessError
from src.modules.identity.domain.user.entity import User
from src.modules.shared import EntityIdVO
from src.modules.identity.domain.user.repository import UserRepositoryProtocol
from src.modules.identity.application.auth.port.tenant_context_reader import (
    TenantContextReaderPort,
)
from src.modules.identity.application.auth.service.otp_service import OtpServiceProtocol
from src.modules.identity.application.access.port.repository import (
    AccessRepositoryProtocol,
)
from src.modules.shared.application.persistence.unit_of_work import UnitOfWorkProtocol
from src.modules.shared.application.tokens.token_manager import TokenManager
from src.modules.identity.application.auth.service.session_issuer import SessionIssuer
from src.modules.identity.application.invitation.service.validator import (
    InvitationValidator,
)
from src.modules.identity.application.invitation.command.accept_invitation.command import (
    AcceptInvitationCommand,
)
from src.modules.identity.application.invitation.command.accept_invitation.dto import (
    AcceptInvitationResultDTO,
)


class AcceptInvitationHandler:

    def __init__(
        self,
        *,
        access: AccessRepositoryProtocol,
        invitations: InvitationValidator,
        issuer: SessionIssuer,
        otp: OtpServiceProtocol,
        tenant_reader: TenantContextReaderPort,
        tokens: TokenManager,
        uow: UnitOfWorkProtocol,
        users: UserRepositoryProtocol,
    ) -> None:
        self.access = access
        self.invitations = invitations
        self.issuer = issuer
        self.otp = otp
        self.tenant_reader = tenant_reader
        self.tokens = tokens
        self.uow = uow
        self.users = users

    async def execute(
        self, request: AcceptInvitationCommand
    ) -> AcceptInvitationResultDTO:
        host = request.host
        invitation_token = request.invitation_token
        token = request.token
        code = request.code
        first_name = request.first_name
        last_name = request.last_name
        context = await self.tenant_reader.get_by_host(host)
        await self.access.lock(context.tenant_id)
        invitation = await self.invitations.valid_invitation(
            context.tenant_id, invitation_token
        )
        # Consume before validation: each challenge permits one submitted code.
        challenge = await self.tokens.consume_token(
            prefix="invitation_otp", suffix=str(context.tenant_id), token=token
        )
        if (
            challenge is None
            or challenge.get("purpose") != "invitation"
            or challenge.get("invitation_id") != str(invitation.id)
            or (challenge.get("email") != invitation.email)
            or (challenge.get("host") != context.host)
            or (challenge.get("domain_id") != str(context.tenant_domain_id))
            or (
                not self.otp.verify_code(code=code, code_hash=challenge.get("hash", ""))
            )
        ):
            raise IdentityAccessError("Verification code is invalid or expired.", 401)
        tenant_id = EntityIdVO.from_value(context.tenant_id)
        if await self.users.exists_by_tenant_and_email(tenant_id, invitation.email):
            raise IdentityAccessError(
                "This email already belongs to a workspace user.", 409
            )
        if not first_name.strip() or not last_name.strip():
            raise IdentityAccessError("First and last name are required.", 422)
        user = User.create_tenant_admin(tenant_id, first_name, last_name)
        user.role = invitation.role
        user.add_email(invitation.email, is_primary=True, is_verified=True)
        await self.users.add(user, tenant_id=tenant_id)
        await self.access.finish_invitation(
            context.tenant_id, invitation.id, "accepted", user.id.uuid
        )
        await self.uow.commit()
        return AcceptInvitationResultDTO(
            context.tenant_id,
            user.id.uuid,
            await self.issuer.issue_session(context, user),
        )
