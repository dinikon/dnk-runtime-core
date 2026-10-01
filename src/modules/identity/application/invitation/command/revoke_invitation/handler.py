from src.modules.identity.domain.access.error import IdentityAccessError
from src.modules.identity.application.access.port.repository import (
    AccessRepositoryProtocol,
)
from src.modules.shared.application.persistence.unit_of_work import UnitOfWorkProtocol
from src.modules.identity.application.auth.service.session_authentication import (
    SessionAuthenticationService,
)
from src.modules.identity.application.invitation.command.revoke_invitation.command import (
    RevokeInvitationCommand,
)
from src.modules.identity.application.invitation.command.revoke_invitation.dto import (
    RevokeInvitationResultDTO,
)


class RevokeInvitationHandler:

    def __init__(
        self,
        *,
        access: AccessRepositoryProtocol,
        authentication: SessionAuthenticationService,
        uow: UnitOfWorkProtocol,
    ) -> None:
        self.access = access
        self.authentication = authentication
        self.uow = uow

    async def execute(
        self, request: RevokeInvitationCommand
    ) -> RevokeInvitationResultDTO:
        host = request.host
        session_token = request.session_token
        invitation_id = request.invitation_id
        context, _, _ = await self.authentication.principal(
            host, session_token, admin=True, locked=True
        )
        invitation = await self.access.invitation(
            context.tenant_id, invitation_id=invitation_id
        )
        if invitation is None:
            raise IdentityAccessError("Invitation not found.", 404)
        if invitation.state == "accepted":
            raise IdentityAccessError("Revoke the accepted user's access instead.", 409)
        await self.access.finish_invitation(context.tenant_id, invitation_id, "revoked")
        await self.uow.commit()
        return RevokeInvitationResultDTO(ok=True)
