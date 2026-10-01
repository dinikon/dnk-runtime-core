from src.modules.identity.domain.access.error import IdentityAccessError
from src.modules.identity.application.auth.port.tenant_context_reader import (
    TenantContextReaderPort,
)
from src.modules.identity.application.access.port.repository import (
    AccessRepositoryProtocol,
)
from src.modules.identity.application.cloud.port.cloud import CloudConnectionReaderPort
from src.modules.identity.application.auth.service.session_authentication import (
    SessionAuthenticationService,
)
from src.modules.identity.application.cloud.query.get_cloud_status.query import (
    GetCloudStatusQuery,
)
from src.modules.identity.application.cloud.query.get_cloud_status.dto import (
    GetCloudStatusResultDTO,
)


class GetCloudStatusHandler:

    def __init__(
        self,
        *,
        access: AccessRepositoryProtocol,
        authentication: SessionAuthenticationService,
        connections: CloudConnectionReaderPort,
        tenant_reader: TenantContextReaderPort,
    ) -> None:
        self.access = access
        self.authentication = authentication
        self.connections = connections
        self.tenant_reader = tenant_reader

    async def execute(self, request: GetCloudStatusQuery) -> GetCloudStatusResultDTO:
        host = request.host
        session_token = request.session_token
        context = await self.tenant_reader.get_by_host(host)
        connection = await self.connections.get(context.tenant_id)
        linked = False
        if session_token:
            try:
                _, user, _ = await self.authentication.principal(host, session_token)
                linked = (
                    await self.access.identity_for_user(context.tenant_id, user.id.uuid)
                    is not None
                )
            except IdentityAccessError:
                pass
        return GetCloudStatusResultDTO(
            **{"enabled": connection is not None, "linked": linked}
        )
