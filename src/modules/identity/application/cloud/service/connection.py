from src.modules.identity.application.auth.port.tenant_context_reader import (
    TenantRequestContext,
)
from src.modules.identity.application.cloud.port.cloud import CloudConnection
from src.modules.identity.domain.access.error import IdentityAccessError
from src.modules.identity.application.cloud.port.cloud import CloudConnectionReaderPort


class CloudConnectionService:

    def __init__(self, *, connections: CloudConnectionReaderPort) -> None:
        self.connections = connections

    async def connection(self, context: TenantRequestContext) -> CloudConnection:
        connection = await self.connections.get(context.tenant_id)
        if connection is None:
            raise IdentityAccessError("Cloud login is not configured.", 404)
        expected = f"https://{context.host}/api/auth/cloud/callback/"
        if connection.callback != expected:
            raise IdentityAccessError(
                "Cloud callback does not match this workspace.", 503
            )
        return connection
