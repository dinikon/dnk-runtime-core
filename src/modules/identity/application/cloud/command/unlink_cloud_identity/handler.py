from uuid import UUID
from src.modules.identity.domain.access.error import IdentityAccessError
from src.modules.identity.application.access.port.repository import (
    AccessRepositoryProtocol,
)
from src.modules.identity.application.cloud.port.cloud import AccessProjectionWriterPort
from src.modules.shared.application.persistence.unit_of_work import UnitOfWorkProtocol
from src.modules.identity.application.auth.service.session_authentication import (
    SessionAuthenticationService,
)
from src.modules.identity.application.cloud.command.unlink_cloud_identity.command import (
    UnlinkCloudIdentityCommand,
)
from src.modules.identity.application.cloud.command.unlink_cloud_identity.dto import (
    UnlinkCloudIdentityResultDTO,
)


class UnlinkCloudIdentityHandler:

    def __init__(
        self,
        *,
        access: AccessRepositoryProtocol,
        authentication: SessionAuthenticationService,
        projections: AccessProjectionWriterPort,
        uow: UnitOfWorkProtocol,
    ) -> None:
        self.access = access
        self.authentication = authentication
        self.projections = projections
        self.uow = uow

    async def execute(
        self, request: UnlinkCloudIdentityCommand
    ) -> UnlinkCloudIdentityResultDTO:
        host = request.host
        session_token = request.session_token
        context, user, _ = await self.authentication.principal(
            host, session_token, locked=True
        )
        if not any(
            (e.is_verified and e.is_primary and (not e.is_deleted) for e in user.emails)
        ):
            raise IdentityAccessError(
                "Verify local OTP access before unlinking your cloud account.", 409
            )
        identity = await self.access.identity_for_user(context.tenant_id, user.id.uuid)
        if identity:
            await self.access.unbind(context.tenant_id, user.id.uuid)
            await self.projections.set_available(
                context.tenant_id, UUID(identity.subject), False, None
            )
        await self.uow.commit()
        return UnlinkCloudIdentityResultDTO(ok=True)
