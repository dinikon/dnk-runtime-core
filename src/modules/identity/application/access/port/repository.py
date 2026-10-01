from typing import Protocol, Any
from uuid import UUID
from src.modules.identity.application.cloud.dto.cloud_identity import CloudIdentity
from src.modules.identity.application.invitation.dto.invitation import Invitation


class AccessRepositoryProtocol(Protocol):

    async def lock(self, tenant_id: UUID) -> None: ...

    async def identity_for_user(
        self, tenant_id: UUID, user_id: UUID
    ) -> CloudIdentity | None: ...

    async def identity_for_subject(
        self, tenant_id: UUID, issuer: str, subject: str
    ) -> CloudIdentity | None: ...

    async def bind(
        self, tenant_id: UUID, user_id: UUID, issuer: str, subject: str
    ) -> None: ...

    async def unbind(self, tenant_id: UUID, user_id: UUID) -> None: ...

    async def list_users(self, tenant_id: UUID) -> list[dict[str, Any]]: ...

    async def change_access(
        self, tenant_id: UUID, user_id: UUID, role: str, status: str
    ) -> None: ...

    async def active_admin_count(self, tenant_id: UUID) -> int: ...

    async def add_invitation(self, tenant_id: UUID, invitation: Invitation) -> None: ...

    async def invitations(self, tenant_id: UUID) -> list[Invitation]: ...

    async def invitation(
        self,
        tenant_id: UUID,
        *,
        token_hash: str | None = None,
        invitation_id: UUID | None = None,
    ) -> Invitation | None: ...

    async def finish_invitation(
        self,
        tenant_id: UUID,
        invitation_id: UUID,
        state: str,
        user_id: UUID | None = None,
    ) -> None: ...
