import hashlib
import secrets
from src.modules.identity.domain.access.error import IdentityAccessError
from src.modules.identity.application.auth.port.tenant_context_reader import (
    TenantContextReaderPort,
)
from src.modules.identity.application.access.port.repository import (
    AccessRepositoryProtocol,
)
from src.modules.identity.application.cloud.port.oidc import OidcClientPort
from src.modules.shared.application.tokens.token_manager import TokenManager
from src.modules.identity.application.auth.service.session_authentication import (
    SessionAuthenticationService,
)
from src.modules.identity.application.cloud.service.connection import (
    CloudConnectionService,
)
from src.modules.identity.application.cloud.command.start_cloud_auth.command import (
    StartCloudAuthCommand,
)
from src.modules.identity.application.cloud.command.start_cloud_auth.dto import (
    StartCloudAuthResultDTO,
)


class StartCloudAuthHandler:

    def __init__(
        self,
        *,
        access: AccessRepositoryProtocol,
        authentication: SessionAuthenticationService,
        cloud_connection: CloudConnectionService,
        oidc: OidcClientPort,
        tenant_reader: TenantContextReaderPort,
        tokens: TokenManager,
    ) -> None:
        self.access = access
        self.authentication = authentication
        self.cloud_connection = cloud_connection
        self.oidc = oidc
        self.tenant_reader = tenant_reader
        self.tokens = tokens

    async def execute(self, request: StartCloudAuthCommand) -> StartCloudAuthResultDTO:
        host = request.host
        session_token = request.session_token
        flow_cookie = request.flow_cookie
        purpose = request.purpose
        context = await self.tenant_reader.get_by_host(host)
        user_id = session_id = None
        epoch = None
        if purpose == "link":
            context, user, session = await self.authentication.principal(
                host, session_token
            )
            if not any(
                (
                    e.is_verified and e.is_primary and (not e.is_deleted)
                    for e in user.emails
                )
            ):
                raise IdentityAccessError(
                    "Verify your primary email with OTP before linking.", 403
                )
            if await self.access.identity_for_user(context.tenant_id, user.id.uuid):
                raise IdentityAccessError("A cloud account is already linked.", 409)
            user_id, session_id, epoch = (
                str(user.id.uuid),
                session.session_id,
                user.session_epoch,
            )
        elif purpose != "login":
            raise IdentityAccessError("Invalid cloud authorization purpose.", 422)
        connection = await self.cloud_connection.connection(context)
        state, nonce, verifier = (
            secrets.token_urlsafe(32),
            secrets.token_urlsafe(32),
            secrets.token_urlsafe(48),
        )
        url = await self.oidc.authorization_url(
            connection, state=state, nonce=nonce, verifier=verifier
        )
        await self.tokens.set_token(
            prefix="oidc_state",
            suffix=str(context.tenant_id),
            token=state,
            body={
                "host": context.host,
                "domain_id": str(context.tenant_domain_id),
                "tenant_id": str(context.tenant_id),
                "issuer": connection.issuer,
                "client_id": connection.client_id,
                "flow_cookie": flow_cookie,
                "session_fingerprint": hashlib.sha256(
                    (session_token or "").encode()
                ).hexdigest(),
                "purpose": purpose,
                "user_id": user_id,
                "session_id": session_id,
                "epoch": epoch,
                "nonce": nonce,
                "verifier": verifier,
            },
            ttl=600,
        )
        return StartCloudAuthResultDTO(authorization_url=url)
