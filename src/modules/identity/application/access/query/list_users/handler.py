from src.modules.identity.application.access.port.repository import (
    AccessRepositoryProtocol,
)
from src.modules.identity.application.auth.service.session_authentication import (
    SessionAuthenticationService,
)
from src.modules.identity.application.access.query.list_users.query import (
    ListUsersQuery,
)
from src.modules.identity.application.access.query.list_users.dto import (
    ListUsersResultDTO,
    UserAccessDTO,
)


class ListUsersHandler:

    def __init__(
        self,
        *,
        access: AccessRepositoryProtocol,
        authentication: SessionAuthenticationService,
    ) -> None:
        self.access = access
        self.authentication = authentication

    async def execute(self, request: ListUsersQuery) -> ListUsersResultDTO:
        host = request.host
        session_token = request.session_token
        context, _, _ = await self.authentication.principal(
            host, session_token, admin=True
        )
        return ListUsersResultDTO(
            [
                UserAccessDTO(**row)
                for row in await self.access.list_users(context.tenant_id)
            ]
        )
