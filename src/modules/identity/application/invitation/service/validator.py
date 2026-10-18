from uuid import UUID
from src.modules.identity.application.invitation.dto.invitation import Invitation
from datetime import UTC, datetime
import hashlib
from src.modules.identity.domain.access.error import IdentityAccessError
from src.modules.identity.application.invitation.dto.invitation import Invitation
from src.modules.identity.application.access.port.repository import (
    AccessRepositoryProtocol,
)


class InvitationValidator:

    def __init__(self, *, access: AccessRepositoryProtocol) -> None:
        self.access = access

    async def valid_invitation(self, tenant_id: UUID, token: str) -> Invitation:
        invitation = await self.access.invitation(
            tenant_id, token_hash=hashlib.sha256(token.encode()).hexdigest()
        )
        if (
            invitation is None
            or invitation.state != "pending"
            or invitation.expires_at <= datetime.now(UTC)
        ):
            raise IdentityAccessError("Invitation is invalid, expired or revoked.", 400)
        return invitation
