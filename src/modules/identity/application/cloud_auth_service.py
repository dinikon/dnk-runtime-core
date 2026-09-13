"""Cloud identity establishes only a local session; local access stays authoritative."""

import secrets
import hashlib
from uuid import UUID

from src.modules.identity.domain.access import IdentityAccessError
from src.modules.identity.domain.user import UserIdVO
from src.modules.shared import EntityIdVO


class CloudAuthService:
    def __init__(self, local, connections, oidc):
        self.local, self.connections, self.oidc = local, connections, oidc

    async def connection(self, context):
        connection = await self.connections.get(context.tenant_id)
        if connection is None:
            raise IdentityAccessError("Cloud login is not configured.", 404)
        expected = f"https://{context.host}/api/auth/cloud/callback/"
        if connection.callback != expected:
            raise IdentityAccessError(
                "Cloud callback does not match this workspace.", 503
            )
        return connection

    async def status(self, host, session_token):
        context = await self.local.context(host)
        connection = await self.connections.get(context.tenant_id)
        linked = False
        if session_token:
            try:
                _, user, _ = await self.local.principal(host, session_token)
                linked = (
                    await self.local.access.identity_for_user(
                        context.tenant_id, user.id.uuid
                    )
                    is not None
                )
            except IdentityAccessError:
                pass
        return {"enabled": connection is not None, "linked": linked}

    async def start(self, host, session_token, flow_cookie, purpose):
        context = await self.local.context(host)
        user_id = session_id = None
        epoch = None
        if purpose == "link":
            context, user, session = await self.local.principal(host, session_token)
            if not any(
                e.is_verified and e.is_primary and not e.is_deleted for e in user.emails
            ):
                raise IdentityAccessError(
                    "Verify your primary email with OTP before linking.", 403
                )
            if await self.local.access.identity_for_user(
                context.tenant_id, user.id.uuid
            ):
                raise IdentityAccessError("A cloud account is already linked.", 409)
            user_id, session_id, epoch = (
                str(user.id.uuid),
                session.session_id,
                user.session_epoch,
            )
        elif purpose != "login":
            raise IdentityAccessError("Invalid cloud authorization purpose.", 422)
        connection = await self.connection(context)
        state, nonce, verifier = (
            secrets.token_urlsafe(32),
            secrets.token_urlsafe(32),
            secrets.token_urlsafe(48),
        )
        url = await self.oidc.authorization_url(
            connection, state=state, nonce=nonce, verifier=verifier
        )
        await self.local.tokens.set_token(
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
        return {"authorization_url": url}

    async def callback(
        self, host, session_token, flow_cookie, *, state, code, issuer, error=None
    ):
        context = await self.local.context(host)
        saved = await self.local.tokens.consume_token(
            prefix="oidc_state", suffix=str(context.tenant_id), token=state
        )
        if (
            saved is None
            or not flow_cookie
            or saved.get("flow_cookie") != flow_cookie
            or saved.get("host") != context.host
            or saved.get("domain_id") != str(context.tenant_domain_id)
            or saved.get("tenant_id") != str(context.tenant_id)
        ):
            raise IdentityAccessError(
                "Cloud authorization state is invalid or expired.", 401
            )
        if (
            saved.get("session_fingerprint")
            != hashlib.sha256((session_token or "").encode()).hexdigest()
        ):
            raise IdentityAccessError("The authorization session has changed.", 401)
        connection = await self.connection(context)
        if (
            issuer != connection.issuer
            or saved.get("issuer") != connection.issuer
            or saved.get("client_id") != connection.client_id
        ):
            raise IdentityAccessError("Cloud authorization issuer does not match.", 401)
        if error or not code:
            raise IdentityAccessError("Cloud authorization was not completed.", 401)
        subject = await self.oidc.exchange(
            connection, code=code, nonce=saved["nonce"], verifier=saved["verifier"]
        )
        await self.local.access.lock(context.tenant_id)
        if saved["purpose"] == "link":
            context, user, session = await self.local.principal(host, session_token)
            if (
                str(user.id.uuid) != saved["user_id"]
                or session.session_id != saved["session_id"]
                or user.session_epoch != saved["epoch"]
            ):
                raise IdentityAccessError("The linking session has changed.", 401)
            if not any(
                e.is_verified and e.is_primary and not e.is_deleted for e in user.emails
            ):
                raise IdentityAccessError("Verified local email is required.", 403)
            await self.local.access.bind(
                context.tenant_id, user.id.uuid, connection.issuer, subject
            )
            await self.local.projections.set_available(
                context.tenant_id, UUID(subject), True
            )
            await self.local.uow.commit()
            return "link", None
        identity = await self.local.access.identity_for_subject(
            context.tenant_id, connection.issuer, subject
        )
        if identity is None:
            raise IdentityAccessError(
                "This cloud account has no local workspace access.", 403
            )
        user = await self.local.users.get_by_id(
            UserIdVO.from_value(identity.user_id),
            tenant_id=EntityIdVO.from_value(context.tenant_id),
        )
        if user is None or not user.can_login():
            raise IdentityAccessError("Local workspace access is unavailable.", 403)
        await self.local.uow.commit()
        session = await self.local.issue_session(context, user)
        return "login", session

    async def unlink(self, host, session_token):
        context, user, _ = await self.local.principal(host, session_token, locked=True)
        if not any(
            e.is_verified and e.is_primary and not e.is_deleted for e in user.emails
        ):
            raise IdentityAccessError(
                "Verify local OTP access before unlinking your cloud account.", 409
            )
        identity = await self.local.access.identity_for_user(
            context.tenant_id, user.id.uuid
        )
        if identity:
            await self.local.access.unbind(context.tenant_id, user.id.uuid)
            await self.local.projections.set_available(
                context.tenant_id, UUID(identity.subject), False
            )
        await self.local.uow.commit()
        return {"ok": True}
