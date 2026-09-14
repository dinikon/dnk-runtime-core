"""Runtime v1 contract and real PostgreSQL failure/concurrency scenarios."""

import asyncio
import copy
import json
import os
import unittest
from datetime import timedelta
from unittest.mock import AsyncMock, patch
from uuid import UUID, uuid4

import httpx
from cryptography.fernet import Fernet
from fastapi import FastAPI
from sqlalchemy import delete, func, select, text, update
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.schema import DropSchema

from src.config.deploy.control_plane import ControlPlaneSettings
from src.modules.control_plane.application.contracts import ProvisioningCommand
from src.modules.control_plane.application.services import (
    AcceptProvisioningCommand,
    ProvisioningConflict,
)
from src.modules.control_plane.application.worker_engine import LostLease
from src.modules.control_plane.infrastructure.crypto import CredentialCipher
from src.modules.control_plane.infrastructure.models import (
    AccessProjectionModel,
    CloudConnectionModel,
    DeliveryModel,
    InstallationModel,
    ProvisioningAttemptModel,
    ReadinessObservationModel,
)
from src.modules.control_plane.infrastructure.readiness import (
    heartbeat_key,
    instance_status,
    probe_hostname,
    save_observation,
    tenant_ready,
)
from src.modules.control_plane.infrastructure.services import (
    AccessProjectionWriter,
    ProvisioningRepository,
    now,
)
from src.modules.control_plane.infrastructure.tenancy_adapter import TenancyAdapter
from src.modules.control_plane.infrastructure.worker_engine import (
    AccessDelivery,
    Installer,
)
from src.modules.shared.infrastructure.persistence.global_migrations import (
    GlobalMigrator,
)
from src.modules.shared.infrastructure.persistence.tenant_migrations import (
    schema_exists,
)
from src.modules.tenancy.infrastructure.persistence.tenant import TenantModel
from src.modules.tenancy.infrastructure.persistence.tenant_domain import (
    TenantDomainModel,
)


def configuration():
    return ControlPlaneSettings(
        public_origin="https://core.example.test",
        management_origin="https://management.core.example.test",
        management_host="manage.runtime.example.test",
        instance_id=uuid4(),
        allowed_base_domains=["one.example.test", "two.example.test"],
        secret_encryption_key=Fernet.generate_key().decode(),
    )


def command_payload():
    tenant_id = uuid4()
    hostname = f"t-{tenant_id.hex}.one.example.test"
    return {
        "tenant_id": str(tenant_id),
        "operation_id": str(uuid4()),
        "attempt_id": str(uuid4()),
        "hostname": hostname,
        "name": "A display name",
        "owner": {
            "sub": str(uuid4()),
            "verified_email": "owner@example.com",
            "profile": {},
        },
        "oidc": {
            "issuer": f"https://core.example.test/oidc/tenants/{tenant_id}",
            "client_id": "client",
            "client_secret": "this-secret-must-not-leak",
            "redirect_uri": f"https://{hostname}/api/auth/cloud/callback/",
        },
    }


class ContractTests(unittest.IsolatedAsyncioTestCase):
    async def test_acceptance_validates_exact_core_payload_before_repository(self):
        repository = AsyncMock()
        config, payload = configuration(), command_payload()
        use_case = AcceptProvisioningCommand(repository, config)
        await use_case(
            ProvisioningCommand.model_validate(payload), payload["attempt_id"]
        )
        _, digest, replay = repository.accept.call_args.args
        self.assertEqual(len(digest), 64)
        self.assertNotIn(payload["oidc"]["client_secret"], replay)
        self.assertEqual(json.loads(replay)["owner"]["sub"], payload["owner"]["sub"])
        with self.assertRaises(ValueError):
            await use_case(ProvisioningCommand.model_validate(payload), str(uuid4()))
        for field, value in [
            ("issuer", "https://evil.test/oidc"),
            ("redirect_uri", "https://evil.test/callback"),
        ]:
            changed = copy.deepcopy(payload)
            changed["oidc"][field] = value
            with self.assertRaises(ValueError):
                await use_case(
                    ProvisioningCommand.model_validate(changed), changed["attempt_id"]
                )

    def test_strict_hostname_zone_and_no_protocol_envelope(self):
        for hostname in [
            "tenant.one.example.test:443",
            "TENANT.one.example.test",
            "tenant.one.example.test.",
            "one.example.test.evil.test",
            "dnk-probe-x.one.example.test",
        ]:
            payload = command_payload()
            payload["hostname"] = hostname
            payload["oidc"][
                "redirect_uri"
            ] = f"https://{hostname}/api/auth/cloud/callback/"
            with self.assertRaises(ValueError, msg=hostname):
                ProvisioningCommand.model_validate(payload).validate_placement(
                    configuration()
                )
        payload = command_payload()
        payload["protocol_version"] = 1
        with self.assertRaises(ValueError):
            ProvisioningCommand.model_validate(payload)


@unittest.skipUnless(
    os.environ.get("TEST_CP_POSTGRES_URL"), "TEST_CP_POSTGRES_URL is required"
)
class RuntimePostgresTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.config = configuration()
        self.engine = create_async_engine(os.environ["TEST_CP_POSTGRES_URL"])
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        async with self.engine.begin() as connection:
            await GlobalMigrator().upgrade(connection)
        self.core_ids = []

    async def asyncTearDown(self):
        async with self.engine.begin() as connection:
            installations = list(
                (
                    await connection.execute(
                        select(InstallationModel.runtime_tenant_id).where(
                            InstallationModel.core_tenant_id.in_(self.core_ids)
                        )
                    )
                ).scalars()
            )
            for tenant_id in installations:
                await connection.execute(
                    DropSchema(f"dnk_{tenant_id.hex}", cascade=True, if_exists=True)
                )
            await connection.execute(
                delete(TenantDomainModel).where(
                    TenantDomainModel.tenant_id.in_(installations)
                )
            )
            await connection.execute(
                delete(TenantModel).where(TenantModel.id.in_(installations))
            )
            for model in [
                DeliveryModel,
                AccessProjectionModel,
                CloudConnectionModel,
                ProvisioningAttemptModel,
                InstallationModel,
            ]:
                await connection.execute(
                    delete(model).where(model.core_tenant_id.in_(self.core_ids))
                )
        await self.engine.dispose()

    async def accept(self, payload=None):
        payload = payload or command_payload()
        core_id = UUID(payload["tenant_id"])
        if core_id not in self.core_ids:
            self.core_ids.append(core_id)
        async with self.sessions() as session, session.begin():
            repository = ProvisioningRepository(
                session, self.config, TenancyAdapter(session, "dnk_")
            )
            result = await AcceptProvisioningCommand(repository, self.config)(
                ProvisioningCommand.model_validate(payload), payload["attempt_id"]
            )
        return payload, result

    async def test_concurrent_replay_creates_one_registry_one_attempt_and_encrypted_replay(
        self,
    ):
        payload = command_payload()
        results = await asyncio.gather(*(self.accept(payload) for _ in range(5)))
        self.assertTrue(all(result.state == "queued" for _, result in results))
        async with self.sessions() as session:
            count = await session.scalar(
                select(func.count())
                .select_from(InstallationModel)
                .where(InstallationModel.core_tenant_id == UUID(payload["tenant_id"]))
            )
            self.assertEqual(count, 1)
            attempt = await session.get(
                ProvisioningAttemptModel, UUID(payload["attempt_id"])
            )
            self.assertNotIn("owner@example.com", attempt.encrypted_command)
            self.assertNotIn(
                payload["oidc"]["client_secret"], attempt.encrypted_command
            )
        altered = copy.deepcopy(payload)
        altered["oidc"]["client_secret"] = "different"
        with self.assertRaises(ProvisioningConflict):
            await self.accept(altered)

    async def test_conflicting_host_and_active_attempt_are_rejected(self):
        payload, _ = await self.accept()
        conflict = copy.deepcopy(payload)
        conflict["attempt_id"] = str(uuid4())
        with self.assertRaises(ProvisioningConflict):
            await self.accept(conflict)
        other = command_payload()
        other["hostname"] = payload["hostname"]
        other["oidc"]["redirect_uri"] = payload["oidc"]["redirect_uri"]
        with self.assertRaises(ProvisioningConflict):
            await self.accept(other)

    async def test_replay_does_not_wait_for_in_progress_schema_transaction(self):
        payload, _ = await self.accept()
        started, release = asyncio.Event(), asyncio.Event()

        class SlowAdapter(TenancyAdapter):
            async def install(self, installation, command):
                await super().install(installation, command)
                started.set()
                await release.wait()

        task = asyncio.create_task(
            Installer(self.sessions, self.config, "dnk_", SlowAdapter).run(
                UUID(payload["attempt_id"])
            )
        )
        try:
            await asyncio.wait_for(started.wait(), timeout=5)
            _, replay = await asyncio.wait_for(self.accept(payload), timeout=1)
            self.assertEqual(replay.state, "running")
        finally:
            release.set()
            await task

    async def test_install_real_schema_owner_secret_projection_and_replay(self):
        payload, _ = await self.accept()
        installer = Installer(self.sessions, self.config, "dnk_")
        await asyncio.gather(
            installer.run(UUID(payload["attempt_id"])),
            installer.run(UUID(payload["attempt_id"])),
        )
        async with self.sessions() as session:
            result = await ProvisioningRepository(session, self.config).lookup(
                UUID(payload["attempt_id"])
            )
            self.assertEqual(
                (result.state, result.resources_state), ("succeeded", "present"), result
            )
            installation = await session.get(
                InstallationModel, UUID(payload["tenant_id"])
            )
            self.assertEqual(
                result.runtime_tenant_id, str(installation.runtime_tenant_id)
            )
            connection = await session.get(
                CloudConnectionModel, installation.runtime_tenant_id
            )
            self.assertEqual(
                CredentialCipher(self.config.secret_encryption_key).decrypt(
                    connection.encrypted_secret
                ),
                payload["oidc"]["client_secret"],
            )
            self.assertEqual(
                await tenant_ready(session, self.config, "dnk_", payload["hostname"]),
                {
                    "tenant_id": payload["tenant_id"],
                    "hostname": payload["hostname"],
                    "ready": True,
                },
            )
            self.assertIsNone(
                await tenant_ready(
                    session, self.config, "dnk_", "unknown.one.example.test"
                )
            )
            projection = await session.get(
                AccessProjectionModel,
                (UUID(payload["tenant_id"]), UUID(payload["owner"]["sub"])),
            )
            self.assertEqual((projection.version, projection.available), (1, True))
        _, replay = await self.accept(payload)
        self.assertEqual(replay.state, "succeeded")
        await installer.run(UUID(payload["attempt_id"]))

    async def test_failure_after_admin_rolls_back_resources_and_allows_next_attempt(
        self,
    ):
        payload, _ = await self.accept()

        class FailingAdapter(TenancyAdapter):
            async def install(self, installation, command):
                await super().install(installation, command)
                raise RuntimeError("Injected failure with fake-secret")

        await Installer(self.sessions, self.config, "dnk_", FailingAdapter).run(
            UUID(payload["attempt_id"])
        )
        async with self.sessions() as session:
            result = await ProvisioningRepository(session, self.config).lookup(
                UUID(payload["attempt_id"])
            )
            self.assertEqual(
                (result.state, result.resources_state), ("failed", "absent")
            )
            installation = await session.get(
                InstallationModel, UUID(payload["tenant_id"])
            )
            self.assertFalse(
                await schema_exists(
                    await session.connection(),
                    f"dnk_{installation.runtime_tenant_id.hex}",
                )
            )
            self.assertIsNone(
                await session.get(TenantModel, installation.runtime_tenant_id)
            )
            self.assertEqual(result.error_code, "installation_failed")
        retry = copy.deepcopy(payload)
        retry["attempt_id"] = str(uuid4())
        await self.accept(retry)
        await Installer(self.sessions, self.config, "dnk_").run(
            UUID(retry["attempt_id"])
        )
        async with self.sessions() as session:
            self.assertEqual(
                (
                    await ProvisioningRepository(session, self.config).lookup(
                        UUID(retry["attempt_id"])
                    )
                ).state,
                "succeeded",
            )

    async def test_missing_attempt_record_never_recreates_registered_tenant(self):
        payload, _ = await self.accept()
        await Installer(self.sessions, self.config, "dnk_").run(
            UUID(payload["attempt_id"])
        )
        async with self.sessions() as session, session.begin():
            await session.execute(
                delete(ProvisioningAttemptModel).where(
                    ProvisioningAttemptModel.attempt_id == UUID(payload["attempt_id"])
                )
            )
        with self.assertRaises(ProvisioningConflict):
            await self.accept(payload)

    async def test_expired_worker_fence_rolls_back_entire_installation(self):
        payload, _ = await self.accept()
        installer = Installer(self.sessions, self.config, "dnk_")
        claim = await installer.claim(UUID(payload["attempt_id"]))
        async with self.sessions() as session, session.begin():
            await session.execute(
                update(ProvisioningAttemptModel)
                .where(ProvisioningAttemptModel.attempt_id == claim.attempt_id)
                .values(lease_until=now() - timedelta(seconds=1))
            )
        with self.assertRaises(LostLease):
            await installer.execute(claim)
        await installer.run(claim.attempt_id)
        async with self.sessions() as session:
            self.assertEqual(
                (
                    await ProvisioningRepository(session, self.config).lookup(
                        claim.attempt_id
                    )
                ).state,
                "succeeded",
            )

    async def test_lease_expiring_during_ddl_cannot_commit_resources(self):
        payload, _ = await self.accept()
        attempt_id = UUID(payload["attempt_id"])

        class ExpiringAdapter(TenancyAdapter):
            async def ready(self, installation, command, **kwargs):
                ready = await super().ready(installation, command, **kwargs)
                await self.session.execute(
                    update(ProvisioningAttemptModel)
                    .where(ProvisioningAttemptModel.attempt_id == attempt_id)
                    .values(lease_until=now() - timedelta(seconds=1))
                )
                return ready

        await Installer(self.sessions, self.config, "dnk_", ExpiringAdapter).run(
            attempt_id
        )
        async with self.sessions() as session, session.begin():
            installation = await session.get(
                InstallationModel, UUID(payload["tenant_id"])
            )
            self.assertIsNone(
                await session.get(TenantModel, installation.runtime_tenant_id)
            )
            self.assertFalse(
                await schema_exists(
                    await session.connection(),
                    f"dnk_{installation.runtime_tenant_id.hex}",
                )
            )
            self.assertIsNone(
                await session.get(
                    AccessProjectionModel,
                    (installation.core_tenant_id, UUID(payload["owner"]["sub"])),
                )
            )
            await session.execute(
                update(ProvisioningAttemptModel)
                .where(ProvisioningAttemptModel.attempt_id == attempt_id)
                .values(lease_until=now() - timedelta(seconds=1))
            )
        await Installer(self.sessions, self.config, "dnk_").run(attempt_id)
        async with self.sessions() as session:
            self.assertEqual(
                (
                    await ProvisioningRepository(session, self.config).lookup(
                        attempt_id
                    )
                ).state,
                "succeeded",
            )

    async def test_replaced_fencing_token_cannot_update_current_attempt(self):
        payload, _ = await self.accept()
        installer = Installer(self.sessions, self.config, "dnk_")
        first = await installer.claim(UUID(payload["attempt_id"]))
        async with self.sessions() as session, session.begin():
            await session.execute(
                update(ProvisioningAttemptModel)
                .where(ProvisioningAttemptModel.attempt_id == first.attempt_id)
                .values(lease_until=now() - timedelta(seconds=1))
            )
        second = await installer.claim(first.attempt_id)
        self.assertGreater(second.token, first.token)
        with self.assertRaises(LostLease):
            await installer.execute(first)
        await installer.execute(second)
        async with self.sessions() as session:
            self.assertEqual(
                (
                    await ProvisioningRepository(session, self.config).lookup(
                        first.attempt_id
                    )
                ).state,
                "succeeded",
            )

    async def test_failed_unknown_retains_reservation_and_cannot_allocate_over_resources(
        self,
    ):
        payload, _ = await self.accept()

        class UnknownAdapter(TenancyAdapter):
            async def inspect(self, *args):
                raise RuntimeError("No authoritative observation")

        await Installer(self.sessions, self.config, "dnk_", UnknownAdapter).run(
            UUID(payload["attempt_id"])
        )
        async with self.sessions() as session:
            result = await ProvisioningRepository(session, self.config).lookup(
                UUID(payload["attempt_id"])
            )
            self.assertEqual(
                (result.state, result.resources_state), ("failed", "unknown")
            )
        changed = copy.deepcopy(payload)
        changed["attempt_id"] = str(uuid4())
        with self.assertRaises(ProvisioningConflict):
            await self.accept(changed)
        # Reconciliation proves absence but does not silently restart installation.
        await Installer(self.sessions, self.config, "dnk_").run(
            UUID(payload["attempt_id"])
        )
        async with self.sessions() as session:
            result = await ProvisioningRepository(session, self.config).lookup(
                UUID(payload["attempt_id"])
            )
            self.assertEqual(
                (result.state, result.resources_state), ("failed", "absent")
            )

    async def test_access_version_survives_revoke_relink_and_http_classification(self):
        payload, _ = await self.accept()
        await Installer(self.sessions, self.config, "dnk_").run(
            UUID(payload["attempt_id"])
        )
        core_id, user_id = UUID(payload["tenant_id"]), UUID(payload["owner"]["sub"])
        async with self.sessions() as session, session.begin():
            installation = await session.get(InstallationModel, core_id)
            writer = AccessProjectionWriter(session)
            self.assertEqual(
                await writer.set_available(
                    installation.runtime_tenant_id, user_id, True
                ),
                1,
            )
            self.assertEqual(
                await writer.set_available(
                    installation.runtime_tenant_id, user_id, False
                ),
                2,
            )
            self.assertEqual(
                await writer.set_available(
                    installation.runtime_tenant_id, user_id, True
                ),
                3,
            )
        async with self.sessions() as session:
            events = list(
                (
                    await session.scalars(
                        select(DeliveryModel)
                        .where(
                            DeliveryModel.core_tenant_id == core_id,
                            DeliveryModel.kind == "access",
                        )
                        .order_by(DeliveryModel.version)
                    )
                ).all()
            )
        replies = [
            httpx.Response(200, json={"status": 200, "data": {"applied": False}}),
            httpx.Response(503),
            httpx.Response(404),
        ]
        sent = []

        def transport(request):
            sent.append(json.loads(request.content))
            return replies.pop(0)

        delivery = AccessDelivery(
            self.sessions, self.config, httpx.MockTransport(transport)
        )
        for event in events:
            await delivery.run(event.event_id)
        async with self.sessions() as session:
            states = [
                (await session.get(DeliveryModel, event.event_id)).state
                for event in events
            ]
            self.assertEqual(states, ["delivered", "pending", "blocked"])
        self.assertEqual([value["version"] for value in sent], [1, 2, 3])
        self.assertEqual(set(sent[0]), {"event_id", "version", "available"})
        # A duplicate broker notification cannot bypass a persisted HTTP backoff.
        await delivery.run(events[1].event_id)
        self.assertEqual(len(sent), 3)
        # A successful HTTP transport with malformed JSON is a contract failure,
        # not a temporary connectivity error or a delivery acknowledgment.
        async with self.sessions() as session, session.begin():
            installation = await session.get(InstallationModel, core_id)
            await AccessProjectionWriter(session).set_available(
                installation.runtime_tenant_id, user_id, False
            )
            malformed_event = await session.scalar(
                select(DeliveryModel).where(
                    DeliveryModel.core_tenant_id == core_id,
                    DeliveryModel.kind == "access",
                    DeliveryModel.version == 4,
                )
            )
        replies.append(httpx.Response(200, content=b"not a JSON response"))
        await delivery.run(malformed_event.event_id)
        async with self.sessions() as session:
            saved = await session.get(DeliveryModel, malformed_event.event_id)
            self.assertEqual(
                (saved.state, saved.error_code), ("blocked", "core_response_invalid")
            )

    async def test_broker_publish_failure_and_lost_notification_recover_from_database(
        self,
    ):
        from src.modules.control_plane.worker import RuntimeWorker

        class Broker:
            def subscriber(self, *args, **kwargs):
                return lambda handler: handler

        class Provider:
            broker = Broker()

        payload, _ = await self.accept()
        worker = RuntimeWorker(self.sessions, self.config, "dnk_", provider=Provider())
        worker.publish = AsyncMock(side_effect=OSError("Broker unavailable"))
        await worker.dispatch()
        async with self.sessions() as session, session.begin():
            event = await session.scalar(
                select(DeliveryModel).where(
                    DeliveryModel.core_tenant_id == UUID(payload["tenant_id"]),
                    DeliveryModel.kind == "install",
                )
            )
            self.assertEqual(
                (event.state, event.error_code), ("pending", "broker_unavailable")
            )
            event.next_attempt_at = now() - timedelta(seconds=1)
        worker.publish = AsyncMock()
        await worker.dispatch()
        worker.publish.assert_awaited_once_with("install", UUID(payload["attempt_id"]))
        # Even after a broker confirmation, authoritative queued attempts are
        # republished if the broker loses the notification before execution.
        worker.publish.reset_mock()
        await worker.reconcile()
        self.assertIn(
            unittest.mock.call("install", UUID(payload["attempt_id"])),
            worker.publish.await_args_list,
        )

    async def test_metrics_read_persisted_step_and_never_emit_identity_details(self):
        from src.modules.control_plane.infrastructure.metrics import render_metrics

        payload, _ = await self.accept()
        await Installer(self.sessions, self.config, "dnk_").run(
            UUID(payload["attempt_id"])
        )
        async with self.sessions() as session:
            metrics = (await render_metrics(session, self.config)).decode()
        self.assertIn("dnk_runtime_installation_step_seconds_max", metrics)
        self.assertIn("dnk_runtime_outbox_oldest_seconds", metrics)
        self.assertIn("dnk_runtime_zone_observation_age_seconds", metrics)
        self.assertNotIn(payload["owner"]["verified_email"], metrics)
        self.assertNotIn(payload["oidc"]["client_secret"], metrics)

    @unittest.skipUnless(
        os.environ.get("TEST_CP_RABBITMQ_URL"), "TEST_CP_RABBITMQ_URL is required"
    )
    async def test_real_rabbitmq_executes_installation_then_access_delivery(self):
        from src.modules.control_plane.worker import EXCHANGE, RuntimeWorker
        from src.modules.shared.infrastructure.messaging import (
            RabbitMQTopologyManager,
            to_rabbit_queue,
        )

        suffix = uuid4().hex
        config = self.config.model_copy(
            update={
                "rabbitmq_url": os.environ["TEST_CP_RABBITMQ_URL"],
                "install_queue": f"dnk.test.install.{suffix}",
                "access_queue": f"dnk.test.access.{suffix}",
            }
        )
        worker = RuntimeWorker(self.sessions, config, "dnk_")
        deliveries = []

        def core(request):
            deliveries.append(json.loads(request.content))
            return httpx.Response(
                200, json={"status": 200, "data": {"applied": True, "version": 1}}
            )

        worker.access.transport = httpx.MockTransport(core)
        await worker.provider.start()
        try:
            topology = RabbitMQTopologyManager(worker.provider)
            for queue in (worker.install_queue, worker.access_queue):
                await topology.bind_queue(
                    queue=queue, exchange=EXCHANGE, routing_key=queue.routing_key
                )
            payload, _ = await self.accept()
            await worker.dispatch()
            async with asyncio.timeout(15):
                while True:
                    async with self.sessions() as session:
                        attempt = await session.get(
                            ProvisioningAttemptModel, UUID(payload["attempt_id"])
                        )
                        if attempt.state == "succeeded":
                            break
                        self.assertNotEqual(attempt.state, "failed")
                    await asyncio.sleep(0.05)
            await worker.dispatch()
            async with asyncio.timeout(10):
                while True:
                    async with self.sessions() as session:
                        event = await session.scalar(
                            select(DeliveryModel).where(
                                DeliveryModel.core_tenant_id
                                == UUID(payload["tenant_id"]),
                                DeliveryModel.kind == "access",
                            )
                        )
                        if event.state == "delivered":
                            break
                    await asyncio.sleep(0.05)
            self.assertEqual(
                deliveries,
                [{"event_id": str(event.event_id), "version": 1, "available": True}],
            )
            await worker.heartbeat()
        finally:
            for queue in (worker.install_queue, worker.access_queue):
                declared = await worker.provider.broker.declare_queue(
                    to_rabbit_queue(queue)
                )
                await declared.delete(if_unused=False, if_empty=False)
            await worker.provider.close()

    async def test_status_observations_are_zone_specific_and_expire(self):
        config = self.config.model_copy(update={"enabled": True})
        async with self.sessions() as session, session.begin():
            await save_observation(session, heartbeat_key(config), True, True)
            await save_observation(session, config.allowed_base_domains[0], True, True)
            await save_observation(session, config.allowed_base_domains[1], True, False)
        async with self.sessions() as session:
            status = await instance_status(session, config)
            self.assertTrue(status.ready)
            self.assertTrue(status.domains[0].tls_ready)
            self.assertFalse(status.domains[1].tls_ready)
        async with self.sessions() as session, session.begin():
            await session.execute(
                update(ReadinessObservationModel).values(
                    observed_at=now() - timedelta(seconds=100)
                )
            )
        async with self.sessions() as session:
            status = await instance_status(session, config)
            self.assertFalse(status.ready)
            self.assertFalse(
                any(d.routing_ready or d.tls_ready for d in status.domains)
            )

    async def test_public_readiness_requires_fresh_worker_but_not_retained_owner_binding(
        self,
    ):
        from src.modules.control_plane.presentation.router import router
        from src.modules.identity.infrastructure.persistence.access import (
            CloudIdentityModel,
        )

        payload, _ = await self.accept()
        await Installer(self.sessions, self.config, "dnk_").run(
            UUID(payload["attempt_id"])
        )
        config = self.config.model_copy(update={"enabled": True})
        app = FastAPI()
        app.state.db, app.state.control_plane_settings = self.sessions, config
        app.include_router(router)
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app),
            base_url=f"https://{payload['hostname']}",
        ) as client:
            self.assertEqual(
                (await client.get("/.well-known/dnk/tenant-ready")).status_code, 503
            )
            async with self.sessions() as session, session.begin():
                await save_observation(session, heartbeat_key(config), True, True)
                installation = await session.get(
                    InstallationModel, UUID(payload["tenant_id"])
                )
                await session.execute(
                    delete(CloudIdentityModel.__table__).execution_options(
                        schema_translate_map={
                            "tenant": f"dnk_{installation.runtime_tenant_id.hex}"
                        }
                    )
                )
            reply = await client.get("/.well-known/dnk/tenant-ready")
            self.assertEqual(reply.status_code, 200, reply.text)
            self.assertEqual(
                reply.json(),
                {
                    "tenant_id": payload["tenant_id"],
                    "hostname": payload["hostname"],
                    "ready": True,
                },
            )

    async def test_http_acceptance_is_committed_and_validation_does_not_echo_secret(
        self,
    ):
        from src.modules.control_plane.presentation.router import router

        app = FastAPI()
        app.state.db = self.sessions
        app.state.control_plane_settings = self.config.model_copy(
            update={"enabled": True}
        )

        @app.middleware("http")
        async def trust(request, call_next):
            request.state.control_plane_trusted = True
            return await call_next(request)

        app.include_router(router)
        payload = command_payload()
        self.core_ids.append(UUID(payload["tenant_id"]))
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app),
            base_url="https://manage.runtime.example.test",
        ) as client:
            reply = await client.post(
                "/internal/v1/tenant-provisioning/",
                json=payload,
                headers={"Idempotency-Key": payload["attempt_id"]},
            )
            self.assertEqual(reply.status_code, 202, reply.text)
            self.assertEqual(reply.json()["state"], "queued")
            self.assertNotIn("data", reply.json())
            async with self.sessions() as observer:
                self.assertIsNotNone(
                    await observer.get(
                        ProvisioningAttemptModel, UUID(payload["attempt_id"])
                    )
                )
            bad = copy.deepcopy(payload)
            bad["unknown_secret"] = "sensitive"
            reply = await client.post("/internal/v1/tenant-provisioning/", json=bad)
            self.assertEqual(reply.status_code, 422)
            self.assertNotIn("sensitive", reply.text)
            reply = await client.get(
                f"/internal/v1/tenant-provisioning/{payload['attempt_id']}/"
            )
            self.assertEqual(reply.status_code, 200)
            self.assertEqual(reply.json()["operation_id"], payload["operation_id"])
