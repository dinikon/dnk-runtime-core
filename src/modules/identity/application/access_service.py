"""Local membership, explicit invitations and opaque session policy."""

from datetime import UTC, datetime, timedelta
import hashlib
import secrets
from uuid import UUID, uuid4

from src.modules.identity.application.ports import SessionRecord
from src.modules.identity.domain.access import IdentityAccessError
from src.modules.identity.application.ports.access import Invitation
from src.modules.identity.domain.user import User, UserIdVO
from src.modules.shared import EntityIdVO
from src.modules.shared.domain.email import SystemEmailKind


def token_digest(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


class IdentityAccessService:
    def __init__(
        self,
        *,
        uow,
        users,
        access,
        sessions,
        tenant_reader,
        tokens,
        otp,
        session_service,
        email,
        settings,
        projections,
    ):
        self.uow, self.users, self.access = uow, users, access
        self.sessions, self.tenant_reader, self.tokens = sessions, tenant_reader, tokens
        self.otp, self.session_service, self.email, self.settings = (
            otp,
            session_service,
            email,
            settings,
        )
        self.projections = projections

    async def context(self, host):
        return await self.tenant_reader.get_by_host(host)

    async def principal(self, host, session_token, *, admin=False, locked=False):
        context = await self.context(host)
        if locked:
            await self.access.lock(context.tenant_id)
        session = (
            await self.sessions.get_session(context.tenant_id, session_token)
            if session_token
            else None
        )
        if session is None or (
            session.host,
            session.tenant_id,
            session.tenant_domain_id,
        ) != (context.host, context.tenant_id, context.tenant_domain_id):
            raise IdentityAccessError("Authentication required.", 401)
        user = await self.users.get_by_id(
            UserIdVO.from_value(session.user_id),
            tenant_id=EntityIdVO.from_value(context.tenant_id),
        )
        if (
            user is None
            or not user.can_login()
            or user.session_epoch != session.session_epoch
        ):
            raise IdentityAccessError("Authentication required.", 401)
        if admin and user.role != "admin":
            raise IdentityAccessError("Administrator access required.", 403)
        return context, user, session

    async def issue_session(self, context, user):
        generated = self.session_service.generate(
            ttl_seconds=self.settings.session_ttl_seconds
        )
        record = SessionRecord(
            token=generated.token,
            session_id=generated.session_id,
            user_id=user.id.uuid,
            tenant_id=context.tenant_id,
            tenant_domain_id=context.tenant_domain_id,
            host=context.host,
            issued_at=generated.issued_at,
            expires_at=generated.expires_at,
            session_epoch=user.session_epoch,
        )
        await self.sessions.create_session(record, self.settings.session_ttl_seconds)
        return record

    async def list_users(self, host, session_token):
        context, _, _ = await self.principal(host, session_token, admin=True)
        return await self.access.list_users(context.tenant_id)

    async def change_user(
        self, host, session_token, user_id, *, role=None, status=None
    ):
        context, _, _ = await self.principal(
            host, session_token, admin=True, locked=True
        )
        user = await self.users.get_by_id(
            UserIdVO.from_value(user_id),
            tenant_id=EntityIdVO.from_value(context.tenant_id),
        )
        if user is None:
            raise IdentityAccessError("User not found.", 404)
        next_role, next_status = role or user.role, status or user.status
        if next_role not in {"admin", "member"} or next_status not in {
            "active",
            "revoked",
        }:
            raise IdentityAccessError("Invalid role or status.", 422)
        if (
            user.role == "admin"
            and user.can_login()
            and (next_role != "admin" or next_status != "active")
            and await self.access.active_admin_count(context.tenant_id) <= 1
        ):
            raise IdentityAccessError(
                "The last active administrator cannot be disabled or demoted.", 409
            )
        if (next_role, next_status) != (user.role, user.status):
            await self.access.change_access(
                context.tenant_id, user.id.uuid, next_role, next_status
            )
            binding = await self.access.identity_for_user(
                context.tenant_id, user.id.uuid
            )
            if binding:
                await self.projections.set_available(
                    context.tenant_id,
                    UUID(binding.subject),
                    next_status == "active",
                    next_role,
                )
        await self.uow.commit()
        return {"ok": True}

    @staticmethod
    def invitation_view(invitation):
        state = invitation.state
        if state == "pending" and invitation.expires_at <= datetime.now(UTC):
            state = "expired"
        return dict(
            id=invitation.id,
            email=invitation.email,
            role=invitation.role,
            state=state,
            expires_at=invitation.expires_at,
        )

    async def list_invitations(self, host, session_token):
        context, _, _ = await self.principal(host, session_token, admin=True)
        return [
            self.invitation_view(i)
            for i in await self.access.invitations(context.tenant_id)
        ]

    async def invite(self, host, session_token, email, role):
        context, user, _ = await self.principal(
            host, session_token, admin=True, locked=True
        )
        email = email.strip().lower()
        if role not in {"admin", "member"}:
            raise IdentityAccessError("Invalid role.", 422)
        if await self.users.exists_by_tenant_and_email(
            EntityIdVO.from_value(context.tenant_id), email
        ):
            raise IdentityAccessError(
                "This email already belongs to a workspace user.", 409
            )
        now = datetime.now(UTC)
        for old in await self.access.invitations(context.tenant_id):
            if old.email == email and old.state == "pending" and old.expires_at > now:
                raise IdentityAccessError(
                    "A pending invitation already exists for this email.", 409
                )
        token = secrets.token_urlsafe(32)
        invitation = Invitation(
            uuid4(),
            email,
            role,
            token_digest(token),
            "pending",
            user.id.uuid,
            None,
            now,
            now + timedelta(days=7),
        )
        await self.access.add_invitation(context.tenant_id, invitation)
        await self.uow.commit()
        scheme = "http" if self.settings.allow_insecure_http else "https"
        return {
            **self.invitation_view(invitation),
            "invitation_url": f"{scheme}://{context.host}/accept-invitation#token={token}",
        }

    async def revoke_invitation(self, host, session_token, invitation_id):
        context, _, _ = await self.principal(
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
        return {"ok": True}

    async def valid_invitation(self, tenant_id, token):
        invitation = await self.access.invitation(
            tenant_id, token_hash=token_digest(token)
        )
        if (
            invitation is None
            or invitation.state != "pending"
            or invitation.expires_at <= datetime.now(UTC)
        ):
            raise IdentityAccessError("Invitation is invalid, expired or revoked.", 400)
        return invitation

    async def request_invitation_otp(self, host, invitation_token):
        context = await self.context(host)
        invitation = await self.valid_invitation(context.tenant_id, invitation_token)
        generated = self.otp.generate()
        await self.tokens.set_token(
            prefix="invitation_otp",
            suffix=str(context.tenant_id),
            token=generated.token,
            body={
                "purpose": "invitation",
                "invitation_id": str(invitation.id),
                "host": context.host,
                "domain_id": str(context.tenant_domain_id),
                "email": invitation.email,
                "hash": generated.code_hash,
            },
            ttl=self.settings.otp_token_ttl_seconds,
        )
        await self.email.send(
            SystemEmailKind.SEND_OTP_CODE,
            invitation.email,
            {"otp_code": generated.code},
        )
        return dict(
            token=generated.token,
            expires_in=self.settings.otp_token_ttl_seconds,
            code=generated.code,
        )

    async def accept_invitation(
        self, host, invitation_token, token, code, first_name, last_name
    ):
        context = await self.context(host)
        await self.access.lock(context.tenant_id)
        invitation = await self.valid_invitation(context.tenant_id, invitation_token)
        # Consume before validating: each challenge permits exactly one submitted code.
        challenge = await self.tokens.consume_token(
            prefix="invitation_otp", suffix=str(context.tenant_id), token=token
        )
        if (
            challenge is None
            or challenge.get("purpose") != "invitation"
            or challenge.get("invitation_id") != str(invitation.id)
            or challenge.get("email") != invitation.email
            or challenge.get("host") != context.host
            or challenge.get("domain_id") != str(context.tenant_domain_id)
            or not self.otp.verify_code(code=code, code_hash=challenge.get("hash", ""))
        ):
            raise IdentityAccessError("Verification code is invalid or expired.", 401)
        tenant_id = EntityIdVO.from_value(context.tenant_id)
        if await self.users.exists_by_tenant_and_email(tenant_id, invitation.email):
            raise IdentityAccessError(
                "This email already belongs to a workspace user.", 409
            )
        if not first_name.strip() or not last_name.strip():
            raise IdentityAccessError("First and last name are required.", 422)
        user = User.create_tenant_admin(tenant_id, first_name, last_name)
        user.role = invitation.role
        user.add_email(invitation.email, is_primary=True, is_verified=True)
        await self.users.add(user, tenant_id=tenant_id)
        await self.access.finish_invitation(
            context.tenant_id, invitation.id, "accepted", user.id.uuid
        )
        await self.uow.commit()
        return context, user, await self.issue_session(context, user)
