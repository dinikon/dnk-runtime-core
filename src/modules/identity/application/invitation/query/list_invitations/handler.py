from src.modules.identity.application.access.port.repository import (
    AccessRepositoryProtocol,
)
from src.modules.identity.application.auth.service.session_authentication import (
    SessionAuthenticationService,
)
from src.modules.identity.application.invitation.service.view import invitation_view
from src.modules.identity.application.invitation.query.list_invitations.query import (
    ListInvitationsQuery,
)
from src.modules.identity.application.invitation.query.list_invitations.dto import (
    ListInvitationsResultDTO,
)


class ListInvitationsHandler:

    def __init__(
        self,
        *,
        access: AccessRepositoryProtocol,
        authentication: SessionAuthenticationService,
    ) -> None:
        self.access = access
        self.authentication = authentication

    async def execute(self, request: ListInvitationsQuery) -> ListInvitationsResultDTO:
        host = request.host
        session_token = request.session_token
        context, _, _ = await self.authentication.principal(
            host, session_token, admin=True
        )
        return ListInvitationsResultDTO(
            [
                invitation_view(i)
                for i in await self.access.invitations(context.tenant_id)
            ]
        )
