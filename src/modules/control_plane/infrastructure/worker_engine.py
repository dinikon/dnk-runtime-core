"""Database-authoritative work execution with expiring fencing tokens."""

import json
import random
import ssl
from datetime import timedelta
from uuid import UUID

import httpx
from sqlalchemy import func, or_, select, update

from src.modules.control_plane.infrastructure.services import (
    AccessProjectionWriter,
    aware,
    now,
    serialize,
)
from src.modules.control_plane.infrastructure.crypto import CredentialCipher
from src.modules.control_plane.infrastructure.models import (
    CloudConnectionModel,
    DeliveryModel,
    InstallationModel,
    DeletionModel,
    ProvisioningAttemptModel,
)
from src.modules.control_plane.infrastructure.tenancy_adapter import TenancyAdapter


from src.modules.control_plane.application.worker_engine import (
    InstallationClaim,
    InstallAttemptUseCase,
    LostLease,
)


def retry_delay(settings, attempts: int) -> float:
    cap = min(
        settings.retry_max_seconds, settings.retry_base_seconds * 2 ** min(attempts, 16)
    )
    return random.uniform(cap / 2, cap)


class Installer:
    def __init__(
        self,
        session_factory,
        settings,
        schema_prefix: str,
        adapter_factory=TenancyAdapter,
    ):
        self.sessions, self.settings, self.schema_prefix = (
            session_factory,
            settings,
            schema_prefix,
        )
        self.adapter_factory = adapter_factory
        self.cipher = CredentialCipher(settings.secret_encryption_key)

    async def run(self, attempt_id: UUID) -> None:
        await InstallAttemptUseCase(self, self.settings.step_timeout_seconds)(
            attempt_id
        )

    async def _locked_attempt(self, session, attempt_id):
        core_id = await session.scalar(
            select(ProvisioningAttemptModel.core_tenant_id).where(
                ProvisioningAttemptModel.attempt_id == attempt_id
            )
        )
        if core_id is None:
            return None
        await serialize(session, f"cp:tenant:{core_id}")
        if await session.get(DeletionModel, core_id):
            return None
        return await session.get(
            ProvisioningAttemptModel,
            attempt_id,
            with_for_update=True,
            populate_existing=True,
        )

    async def claim(self, attempt_id: UUID) -> InstallationClaim | None:
        async with self.sessions() as session, session.begin():
            attempt = await self._locked_attempt(session, attempt_id)
            if (
                attempt is None
                or attempt.state == "succeeded"
                or (attempt.state == "failed" and attempt.resources_state == "absent")
            ):
                return None
            installation = await session.get(InstallationModel, attempt.core_tenant_id)
            if installation is None or installation.current_attempt_id != attempt_id:
                return None
            if (
                attempt.state == "running"
                and attempt.lease_until
                and aware(attempt.lease_until) > now()
            ):
                return None
            was_failed = attempt.state == "failed"
            attempt.state = "running"
            attempt.step = "reconcile" if was_failed else "installing"
            attempt.fencing_token += 1
            attempt.lease_until = now() + timedelta(seconds=self.settings.lease_seconds)
            attempt.updated_at = now()
            return InstallationClaim(attempt_id, attempt.fencing_token, was_failed)

    async def execute(self, claim: InstallationClaim) -> None:
        async with self.sessions() as session, session.begin():
            attempt, installation = await self._owned(
                session, claim.attempt_id, claim.token
            )
            command = json.loads(self.cipher.decrypt(attempt.encrypted_command))
            adapter = self.adapter_factory(session, self.schema_prefix)
            resources = await adapter.inspect(
                installation.runtime_tenant_id,
                installation.hostname,
                str(installation.core_tenant_id),
            )
            if resources == "absent":
                if claim.reconciling_failure:
                    await self._finish(
                        session,
                        attempt,
                        claim.token,
                        "failed",
                        "absent",
                        "resources_absent",
                    )
                    return
                await adapter.install(installation, command)
                await AccessProjectionWriter(session).set_available(
                    installation.runtime_tenant_id,
                    UUID(command["owner"]["sub"]),
                    True,
                )
            elif resources != "present":
                raise RuntimeError("Unconfirmed resources")
            connection = await session.get(
                CloudConnectionModel, installation.runtime_tenant_id
            )
            if connection is None or not self.cipher.decrypt(
                connection.encrypted_secret
            ):
                raise RuntimeError("Missing cloud credential")
            if not await adapter.ready(installation, command):
                raise RuntimeError("Local installation is incomplete")
            await adapter.activate(installation.runtime_tenant_id)
            await self._finish(
                session, attempt, claim.token, "succeeded", "present", None
            )

    async def _owned(self, session, attempt_id, token):
        attempt = await self._locked_attempt(session, attempt_id)
        if (
            attempt is None
            or attempt.state != "running"
            or attempt.fencing_token != token
            or not attempt.lease_until
            or aware(attempt.lease_until) <= now()
        ):
            raise LostLease()
        installation = await session.get(InstallationModel, attempt.core_tenant_id)
        if installation is None or installation.current_attempt_id != attempt_id:
            raise LostLease()
        return attempt, installation

    async def _finish(self, session, attempt, token, state, resources, error):
        # PostgreSQL clock_timestamp, unlike transaction_timestamp, advances during DDL.
        current_time = (
            func.clock_timestamp()
            if session.get_bind().dialect.name == "postgresql"
            else now()
        )
        result = await session.execute(
            update(ProvisioningAttemptModel)
            .where(
                ProvisioningAttemptModel.attempt_id == attempt.attempt_id,
                ProvisioningAttemptModel.state == "running",
                ProvisioningAttemptModel.fencing_token == token,
                ProvisioningAttemptModel.lease_until > current_time,
            )
            .values(
                state=state,
                resources_state=resources,
                error_code=error,
                step_duration_ms=max(
                    0, int((now() - aware(attempt.updated_at)).total_seconds() * 1000)
                ),
                step="complete" if state == "succeeded" else "reconcile",
                lease_until=None,
                next_attempt_at=now()
                + timedelta(seconds=self.settings.reconcile_interval_seconds),
                updated_at=now(),
            )
            .execution_options(synchronize_session=False)
        )
        if result.rowcount != 1:
            raise LostLease()

    async def record_failure(self, attempt_id, token):
        try:
            async with self.sessions() as session, session.begin():
                attempt, installation = await self._owned(session, attempt_id, token)
                try:
                    # SAVEPOINT makes a failed inspector leave a usable transaction.
                    async with session.begin_nested():
                        resources = await self.adapter_factory(
                            session, self.schema_prefix
                        ).inspect(
                            installation.runtime_tenant_id,
                            installation.hostname,
                            str(installation.core_tenant_id),
                        )
                except Exception:
                    resources = "unknown"
                await self._finish(
                    session, attempt, token, "failed", resources, "installation_failed"
                )
        except LostLease:
            pass
        # If DB itself is unavailable the committed running lease remains durable;
        # the recovery scanner retries after it expires, never assumes absence.


class AccessDelivery:
    def __init__(self, session_factory, settings, transport=None):
        self.sessions, self.settings, self.transport = (
            session_factory,
            settings,
            transport,
        )

    def tls_context(self):
        context = ssl.create_default_context(
            cafile=self.settings.ca_bundle_path or None
        )
        context.load_cert_chain(
            self.settings.client_cert_path, self.settings.client_key_path
        )
        return context

    async def run(self, event_id: UUID) -> None:
        from src.modules.shared.infrastructure.persistence.tenant_gate import (
            TenantGate,
            TenantUnavailable,
        )

        async with self.sessions() as session:
            runtime_id = await session.scalar(
                select(InstallationModel.runtime_tenant_id)
                .join(
                    DeliveryModel,
                    DeliveryModel.core_tenant_id == InstallationModel.core_tenant_id,
                )
                .where(DeliveryModel.event_id == event_id)
            )
        if runtime_id is None:
            return
        try:
            async with TenantGate(self.sessions).hold(runtime_id):
                await self._run(event_id)
        except TenantUnavailable:
            return

    async def _run(self, event_id: UUID) -> None:
        async with self.sessions() as session, session.begin():
            event = await session.get(DeliveryModel, event_id, with_for_update=True)
            if (
                event is None
                or event.kind != "access"
                or event.state in {"delivered", "blocked"}
            ):
                return
            if await session.get(DeletionModel, event.core_tenant_id):
                event.state = "delivered"
                event.delivered_at = now()
                return
            if event.state == "pending" and aware(event.next_attempt_at) > now():
                return
            if (
                event.state == "running"
                and event.lease_until
                and aware(event.lease_until) > now()
            ):
                return
            event.state = "running"
            event.fencing_token += 1
            event.attempts += 1
            event.lease_until = now() + timedelta(seconds=self.settings.lease_seconds)
            token, payload, attempts = (
                event.fencing_token,
                dict(event.payload),
                event.attempts,
            )
            path = f"/internal/v1/tenants/{event.core_tenant_id}/access/{event.aggregate_id}/"
        state, error = "pending", "core_unavailable"
        try:
            verify = self.tls_context() if self.transport is None else True
            async with httpx.AsyncClient(
                base_url=self.settings.management_origin,
                verify=verify,
                transport=self.transport,
                trust_env=False,
                follow_redirects=False,
                timeout=self.settings.request_timeout_seconds,
            ) as client:
                reply = await client.put(path, json=payload)
            if reply.status_code == 200:
                try:
                    body = reply.json()
                except ValueError:
                    body = None
                data = body.get("data") if isinstance(body, dict) else None
                valid = (
                    isinstance(data, dict)
                    and type(data.get("applied")) is bool
                    and body.get("status") == 200
                )
                if valid and data["applied"]:
                    valid = (
                        type(data.get("version")) is int
                        and data["version"] == payload["version"]
                    )
                elif valid and "version" in data:
                    valid = (
                        type(data["version"]) is int
                        and data["version"] >= payload["version"]
                    )
                if valid:
                    state, error = "delivered", None
                else:
                    state, error = "blocked", "core_response_invalid"
            elif (
                reply.status_code in {401, 403, 404, 409}
                or (400 <= reply.status_code < 500 and reply.status_code != 429)
                or 300 <= reply.status_code < 400
            ):
                state, error = "blocked", f"core_http_{reply.status_code}"
            elif reply.status_code != 429 and reply.status_code < 500:
                state, error = "blocked", "core_response_invalid"
        except (httpx.HTTPError, ValueError, OSError):
            pass
        async with self.sessions() as session, session.begin():
            current_time = (
                func.clock_timestamp()
                if session.get_bind().dialect.name == "postgresql"
                else now()
            )
            await session.execute(
                update(DeliveryModel)
                .where(
                    DeliveryModel.event_id == event_id,
                    DeliveryModel.state == "running",
                    DeliveryModel.fencing_token == token,
                    DeliveryModel.lease_until > current_time,
                )
                .values(
                    state=state,
                    error_code=error,
                    lease_until=None,
                    next_attempt_at=now()
                    + timedelta(seconds=retry_delay(self.settings, attempts)),
                    delivered_at=now() if state == "delivered" else None,
                )
            )


async def due_attempts(session, limit: int = 100):
    stamp = now()
    return list(
        (
            await session.scalars(
                select(ProvisioningAttemptModel.attempt_id)
                .where(
                    ~ProvisioningAttemptModel.core_tenant_id.in_(
                        select(DeletionModel.core_tenant_id)
                    ),
                    or_(
                        ProvisioningAttemptModel.state == "queued",
                        (ProvisioningAttemptModel.state == "running")
                        & (ProvisioningAttemptModel.lease_until <= stamp),
                        (ProvisioningAttemptModel.state == "failed")
                        & (ProvisioningAttemptModel.resources_state != "absent"),
                    ),
                    or_(
                        ProvisioningAttemptModel.next_attempt_at.is_(None),
                        ProvisioningAttemptModel.next_attempt_at <= stamp,
                    ),
                )
                .order_by(ProvisioningAttemptModel.created_at)
                .limit(limit)
            )
        ).all()
    )
