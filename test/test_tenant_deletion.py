"""Real PostgreSQL deletion, late-delivery fences and admission drain races."""

import asyncio
import os
import unittest
from unittest.mock import AsyncMock, patch
from uuid import UUID, uuid4

import httpx
from fastapi import FastAPI, Request
from src.modules.shared.presentation.persistence.depends import UoWDep
from sqlalchemy import delete, select, func, update, text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from test.test_control_plane_runtime import configuration, command_payload
from src.modules.control_plane.application.contracts import (
    DeletionCommand,
    PurgeCommand,
    ProvisioningCommand,
)
from src.modules.control_plane.application.services import (
    AcceptProvisioningCommand,
    ProvisioningConflict,
)
from src.modules.control_plane.infrastructure.deletion import (
    DeletionRepository,
    DeletionWorker,
    DeletionError,
)
from src.modules.control_plane.infrastructure.models import (
    DeletionModel,
    InstallationModel,
    ProvisioningAttemptModel,
    AccessProjectionModel,
    CloudConnectionModel,
    DeliveryModel,
)
from src.modules.control_plane.infrastructure.services import (
    ProvisioningRepository,
    now,
)
from src.modules.control_plane.infrastructure.tenancy_adapter import TenancyAdapter
from src.modules.control_plane.infrastructure.worker_engine import Installer
from src.modules.shared.infrastructure.persistence.global_migrations import (
    GlobalMigrator,
)
from src.modules.shared.infrastructure.persistence.tenant_gate import (
    TenantGate,
    TenantUnavailable,
    gate_key,
)
from src.modules.shared.infrastructure.persistence.tenant_migrations import (
    schema_exists,
)
from src.modules.shared.presentation.http.tenant_gate import TenantAdmissionMiddleware
from src.modules.tenancy.infrastructure.persistence.tenant import TenantModel
from src.modules.tenancy.infrastructure.persistence.tenant_domain import (
    TenantDomainModel,
)
from src.modules.identity.infrastructure.repository.access_repository import (
    AccessRepository,
)
from src.modules.identity.infrastructure.persistence.user import UserModel
from src.modules.shared.application.persistence.tenant_schema_naming import (
    TenantSchemaNaming,
)
from src.modules.shared.infrastructure.jobs.scheduled_job_model import ScheduledJobModel
from src.modules.shared.infrastructure.events.integration_outbox_event_model import (
    IntegrationOutboxEventModel,
)
from src.modules.shared.infrastructure.events.integration_inbox_event_model import (
    IntegrationInboxEventModel,
)


@unittest.skipUnless(
    os.environ.get("TEST_CP_POSTGRES_URL"), "TEST_CP_POSTGRES_URL required"
)
class TenantDeletionTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine(os.environ["TEST_CP_POSTGRES_URL"])
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        self.settings = configuration()
        self.eraser = AsyncMock()
        self.worker = DeletionWorker(self.sessions, self.settings, "dnk_", self.eraser)
        self.payloads = []
        async with self.engine.begin() as connection:
            await GlobalMigrator().upgrade(connection)

    async def asyncTearDown(self):
        # Clean only the UUIDs allocated by this test, using the actual operator path.
        for payload in self.payloads:
            cmd = self.command(payload, source="operator")
            async with self.sessions() as session, session.begin():
                row = await session.get(DeletionModel, cmd.tenant_id)
                if row:
                    cmd.operation_id = row.operation_id
                else:
                    await self.repo(session).accept(cmd)
            await self.worker.run(cmd.operation_id)
            async with self.sessions() as session, session.begin():
                row = await session.get(DeletionModel, cmd.tenant_id)
                if row.state == "blocked":
                    await self.repo(session).request_purge(
                        cmd.operation_id,
                        PurgeCommand(tenant_id=cmd.tenant_id, version=2),
                    )
            await self.worker.run(cmd.operation_id)
            async with self.sessions() as session, session.begin():
                row = await session.get(DeletionModel, cmd.tenant_id)
                self.assertEqual(row.state, "deleted", row.error_code)
                await session.delete(row)
        await self.engine.dispose()

    def repo(self, session):
        return DeletionRepository(session, self.settings, "dnk_")

    def command(self, payload, source="user"):
        return DeletionCommand(
            tenant_id=payload["tenant_id"],
            operation_id=uuid4(),
            hostname=payload["hostname"],
            initiator_id=payload["owner"]["sub"],
            source=source,
        )

    async def install(self, *, run=True):
        payload = command_payload()
        self.payloads.append(payload)
        async with self.sessions() as session, session.begin():
            repository = ProvisioningRepository(
                session, self.settings, TenancyAdapter(session, "dnk_")
            )
            await AcceptProvisioningCommand(repository, self.settings)(
                ProvisioningCommand.model_validate(payload), payload["attempt_id"]
            )
        if run:
            await Installer(self.sessions, self.settings, "dnk_").run(
                UUID(payload["attempt_id"])
            )
        async with self.sessions() as session:
            installation = await session.get(
                InstallationModel, UUID(payload["tenant_id"])
            )
            return payload, installation.runtime_tenant_id

    async def accept(self, command):
        async with self.sessions() as session, session.begin():
            return await self.repo(session).accept(command)

    async def test_busy_tenants_do_not_starve_later_deletions(self):
        ids = [uuid4() for _ in range(101)]
        runtime_ids = [uuid4() for _ in ids]
        try:
            async with self.sessions() as session, session.begin():
                for operation_id, runtime_id in zip(ids, runtime_ids):
                    session.add(
                        DeletionModel(
                            core_tenant_id=uuid4(),
                            runtime_tenant_id=runtime_id,
                            operation_id=operation_id,
                            state="deletion_pending",
                            version=1,
                            command_hash="0" * 64,
                            creation_succeeded=False,
                            updated_at=now(),
                        )
                    )
            # Model 100 admitted handlers that keep running while a later
            # unrelated tenant can already complete its drain.
            async with self.engine.begin() as busy:
                for runtime_id in runtime_ids[:-1]:
                    await busy.execute(
                        text("SELECT pg_advisory_xact_lock_shared(:key)"),
                        {"key": gate_key(runtime_id)},
                    )
                await self.worker.due()
                await self.worker.due()
                async with self.sessions() as session:
                    states = dict(
                        (
                            await session.execute(
                                select(
                                    DeletionModel.operation_id, DeletionModel.state
                                ).where(DeletionModel.operation_id.in_(ids))
                            )
                        ).all()
                    )
                self.assertEqual(states[ids[-1]], "blocked")
                self.assertTrue(
                    all(
                        states[operation_id] == "deletion_pending"
                        for operation_id in ids[:-1]
                    )
                )
        finally:
            async with self.sessions() as session, session.begin():
                await session.execute(
                    delete(DeletionModel).where(DeletionModel.operation_id.in_(ids))
                )

    async def state(self, command):
        async with self.sessions() as session:
            return await self.repo(session).lookup(command.operation_id)

    async def purge(self, command):
        async with self.sessions() as session, session.begin():
            return await self.repo(session).request_purge(
                command.operation_id,
                PurgeCommand(tenant_id=command.tenant_id, version=2),
            )

    async def seed_shared(self, tenant_id):
        async with self.sessions() as session, session.begin():
            session.add(
                ScheduledJobModel(
                    id=uuid4(),
                    tenant_id=tenant_id,
                    job_type="test",
                    payload={"secret": "delete me"},
                    run_at=now(),
                )
            )
            session.add(
                IntegrationOutboxEventModel(
                    id=uuid4(),
                    tenant_id=tenant_id,
                    event_type="test",
                    event_version=1,
                    aggregate_type="test",
                    aggregate_id=uuid4(),
                    payload={"secret": "delete me"},
                    occurred_at=now(),
                )
            )
            session.add(
                IntegrationInboxEventModel(
                    tenant_id=tenant_id,
                    source="test",
                    message_id=str(uuid4()),
                    event_type="test",
                )
            )

    async def test_full_purge_removes_schema_models_and_secrets_but_preserves_neighbor(
        self,
    ):
        payload, runtime_id = await self.install()
        neighbor, neighbor_id = await self.install()
        await self.seed_shared(runtime_id)
        await self.seed_shared(neighbor_id)
        command = self.command(payload)
        self.assertEqual((await self.accept(command)).state, "deletion_pending")
        with self.assertRaises(DeletionError):
            await self.purge(command)
        await self.worker.run(command.operation_id)
        self.assertEqual((await self.state(command)).state, "blocked")
        self.assertEqual((await self.purge(command)).state, "purging")
        await self.worker.run(command.operation_id)
        self.assertEqual((await self.state(command)).resources_state, "absent")
        self.assertEqual((await self.accept(command)).state, "deleted")
        async with self.sessions() as session:
            self.assertFalse(
                await schema_exists(await session.connection(), f"dnk_{runtime_id.hex}")
            )
            self.assertTrue(
                await schema_exists(
                    await session.connection(), f"dnk_{neighbor_id.hex}"
                )
            )
            self.assertIsNone(await session.get(TenantModel, runtime_id))
            self.assertEqual(
                (await session.get(TenantModel, neighbor_id)).status, "active"
            )
            for model in (
                ScheduledJobModel,
                IntegrationOutboxEventModel,
                IntegrationInboxEventModel,
            ):
                self.assertEqual(
                    await session.scalar(
                        select(func.count())
                        .select_from(model)
                        .where(model.tenant_id == runtime_id)
                    ),
                    0,
                )
                self.assertEqual(
                    await session.scalar(
                        select(func.count())
                        .select_from(model)
                        .where(model.tenant_id == neighbor_id)
                    ),
                    1,
                )
            for model in (
                InstallationModel,
                ProvisioningAttemptModel,
                AccessProjectionModel,
                CloudConnectionModel,
                DeliveryModel,
            ):
                count = await session.scalar(
                    select(func.count())
                    .select_from(model)
                    .where(model.core_tenant_id == command.tenant_id)
                )
                self.assertEqual(count, 0, model.__name__)
            receipt = await session.get(DeletionModel, command.tenant_id)
            self.assertIsNone(receipt.command)
            self.assertIsNone(receipt.error_code)
        changed = command.model_copy(update={"hostname": "changed.one.example.test"})
        with self.assertRaises(DeletionError):
            await self.accept(changed)

    async def test_current_role_is_checked_under_membership_lock(self):
        payload, runtime_id = await self.install()
        command = self.command(payload)
        async with self.sessions() as session, session.begin():
            access = AccessRepository(session, TenantSchemaNaming("dnk_"))
            await access.lock(runtime_id)
            binding = await access.identity_for_subject(
                runtime_id, payload["oidc"]["issuer"], payload["owner"]["sub"]
            )
            await access.change_access(runtime_id, binding.user_id, "member", "active")
        with self.assertRaises(DeletionError) as denied:
            await self.accept(command)
        self.assertEqual(denied.exception.status, 403)
        self.assertIsNone(await self.state(command))
        async with self.sessions() as session:
            self.assertEqual(
                (await session.get(TenantModel, runtime_id)).status, "active"
            )

    async def test_admission_spans_http_handler_commits_and_drains_before_blocked(self):
        payload, runtime_id = await self.install()
        entered, finish = asyncio.Event(), asyncio.Event()
        app = FastAPI()
        app.state.db = self.sessions
        app.add_middleware(TenantAdmissionMiddleware)

        @app.get("/work")
        async def work(request: Request, uow: UoWDep):
            self.assertIs(
                await uow.session.connection(), request.state.tenant_connection
            )
            await uow.session.execute(select(func.count()).select_from(TenantModel))
            await uow.commit()
            entered.set()
            await finish.wait()
            self.assertIs(
                await uow.session.connection(), request.state.tenant_connection
            )
            await uow.session.execute(select(func.count()).select_from(TenantModel))
            return {"done": True}

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url=f"https://{payload['hostname']}",
        ) as client:
            running = asyncio.create_task(client.get("/work"))
            await asyncio.wait_for(entered.wait(), 5)
            command = self.command(payload)
            await self.accept(command)
            await self.worker.run(command.operation_id)
            self.assertEqual((await self.state(command)).state, "deletion_pending")
            self.assertEqual((await client.get("/work")).status_code, 403)
            finish.set()
            self.assertEqual((await running).status_code, 200)
        await self.worker.run(command.operation_id)
        self.assertEqual((await self.state(command)).state, "blocked")

    async def test_old_provisioning_command_and_worker_cannot_resurrect_tenant(self):
        payload, runtime_id = await self.install(run=False)
        command = self.command(payload, source="operator")
        await self.accept(command)
        await Installer(self.sessions, self.settings, "dnk_").run(
            UUID(payload["attempt_id"])
        )
        async with self.sessions() as session:
            self.assertIsNone(await session.get(TenantModel, runtime_id))
        await self.worker.run(command.operation_id)
        await self.purge(command)
        await self.worker.run(command.operation_id)
        with self.assertRaises(ProvisioningConflict):
            async with self.sessions() as session, session.begin():
                await AcceptProvisioningCommand(
                    ProvisioningRepository(session, self.settings), self.settings
                )(ProvisioningCommand.model_validate(payload), payload["attempt_id"])

    async def test_operator_can_fence_a_tenant_never_received_by_runtime(self):
        payload = command_payload()
        self.payloads.append(payload)
        command = self.command(payload, source="operator")
        await self.accept(command)
        await self.worker.run(command.operation_id)
        await self.purge(command)
        await self.worker.run(command.operation_id)
        receipt = await self.state(command)
        self.assertEqual(receipt.state, "deleted")
        self.assertIsNone(receipt.runtime_tenant_id)

    async def test_redis_failure_keeps_data_blocked_and_retry_completes(self):
        payload, runtime_id = await self.install()
        command = self.command(payload)
        await self.accept(command)
        await self.worker.run(command.operation_id)
        await self.purge(command)
        self.eraser.side_effect = OSError("redis unavailable")
        await self.worker.run(command.operation_id)
        self.assertEqual((await self.state(command)).state, "purging")
        async with self.sessions() as session:
            self.assertTrue(
                await schema_exists(await session.connection(), f"dnk_{runtime_id.hex}")
            )
        self.eraser.side_effect = None
        await self.worker.run(command.operation_id)
        self.assertEqual((await self.state(command)).state, "deleted")

    async def test_conflicting_operation_or_placement_is_rejected(self):
        payload, runtime_id = await self.install()
        command = self.command(payload)
        command.runtime_tenant_id = uuid4()
        with self.assertRaises(DeletionError):
            await self.accept(command)
        command.runtime_tenant_id = runtime_id
        await self.accept(command)
        with self.assertRaises(DeletionError):
            await self.accept(self.command(payload))

    async def test_all_public_business_routes_are_denied_before_auth_or_data_access(
        self,
    ):
        from src.app_factory import create_app
        from src.modules.shared.infrastructure.tokens.redis_token_repository import (
            RedisTokenRepository,
        )

        payload, _ = await self.install()
        command = self.command(payload)
        await self.accept(command)
        await self.worker.run(command.operation_id)
        app = create_app()
        app.state.db = self.sessions
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url=f"https://{payload['hostname']}",
        ) as client:
            with patch.object(
                RedisTokenRepository,
                "from_config",
                side_effect=AssertionError("Business auth must not run"),
            ):
                for path, methods in app.openapi()["paths"].items():
                    if not path.startswith("/api/"):
                        continue
                    path = path.replace("{user_id}", str(uuid4())).replace(
                        "{invitation_id}", str(uuid4())
                    )
                    for method in methods:
                        response = await client.request(method, path, json={})
                        self.assertEqual(
                            response.status_code, 403, (method, path, response.text)
                        )
                        self.assertEqual(response.json()["code"], "tenant_unavailable")

    async def test_background_handlers_cannot_run_or_persist_inbox_after_purge(self):
        from src.modules.shared.domain.events import IntegrationEvent
        from src.modules.shared.application.events import (
            HandleIntegrationEventCommand,
            PublishOutboxEventsCommand,
        )
        from src.modules.shared.application.jobs import (
            ProcessDueScheduledJobsCommand,
            ScheduleScheduledJobCommand,
        )
        from src.modules.shared.presentation.events.management import (
            build_idempotent_event_consumer,
            build_publish_outbox_events_use_case,
        )
        from src.modules.shared.presentation.jobs.management import (
            build_process_due_scheduled_jobs_use_case,
            build_schedule_scheduled_job_use_case,
        )

        payload, runtime_id = await self.install()
        await self.seed_shared(runtime_id)
        command = self.command(payload)
        await self.accept(command)
        await self.worker.run(command.operation_id)
        handler, publisher, dispatcher = AsyncMock(), AsyncMock(), AsyncMock()
        async with self.sessions() as session, session.begin():
            await build_process_due_scheduled_jobs_use_case(
                session=session, dispatcher=dispatcher, retry_base_seconds=1
            )(ProcessDueScheduledJobsCommand())
            await build_publish_outbox_events_use_case(
                session=session, publisher=publisher, retry_base_seconds=1
            )(PublishOutboxEventsCommand())
        dispatcher.dispatch.assert_not_awaited()
        publisher.publish.assert_not_awaited()
        await self.purge(command)
        await self.worker.run(command.operation_id)
        async with self.sessions() as session, session.begin():
            consumer = build_idempotent_event_consumer(session=session, handler=handler)
            event = IntegrationEvent(
                uuid4(),
                runtime_id,
                "test",
                1,
                "test",
                uuid4(),
                {"must_not_persist": True},
                now(),
            )
            await consumer(
                HandleIntegrationEventCommand(source="test", message_id=str(uuid4())),
                event,
            )
            with self.assertRaises(TenantUnavailable):
                await build_schedule_scheduled_job_use_case(session=session)(
                    ScheduleScheduledJobCommand(runtime_id, "test", {}, now())
                )
            self.assertEqual(
                await session.scalar(
                    select(func.count())
                    .select_from(IntegrationInboxEventModel)
                    .where(IntegrationInboxEventModel.tenant_id == runtime_id)
                ),
                0,
            )
        handler.handle.assert_not_awaited()
        import io
        from src.modules.shared.infrastructure.events.rabbitmq_integration_event_console_worker import (
            handle_integration_event_console_message,
        )

        message, output = AsyncMock(), io.StringIO()
        await handle_integration_event_console_message(
            payload={"tenant_id": str(runtime_id), "payload": {"must_not_log": True}},
            message=message,
            output=output,
            admission=TenantGate(self.sessions).hold,
        )
        message.ack.assert_awaited_once()
        message.reject.assert_not_awaited()
        self.assertEqual(output.getvalue(), "")

    @unittest.skipUnless(
        os.environ.get("TEST_DELETION_REDIS_URL"), "Disposable Redis required"
    )
    async def test_real_redis_namespace_cleanup_preserves_neighbor(self):
        from redis.asyncio import Redis
        from src.modules.control_plane.infrastructure.deletion import erase_tokens
        from src.modules.shared.infrastructure.tokens.redis_token_repository import (
            RedisTokenRepository,
        )

        payload, runtime_id = await self.install()
        neighbor_id, neighbor_host = uuid4(), f"{uuid4().hex}.one.example.test"

        def keys(tenant_id, host):
            return [
                f"{p}:{tenant_id}:{uuid4()}"
                for p in ("session", "otp_login", "oidc_state", "invitation_otp")
            ] + [f"csrf:{host}:{uuid4()}"]

        removed, preserved = keys(runtime_id, payload["hostname"]), keys(
            neighbor_id, neighbor_host
        )
        client = Redis.from_url(os.environ["TEST_DELETION_REDIS_URL"])
        try:
            await client.mset({key: "test-only" for key in removed + preserved})
            command = self.command(payload)
            await self.accept(command)
            await self.worker.run(command.operation_id)
            await self.purge(command)
            worker = DeletionWorker(self.sessions, self.settings, "dnk_", erase_tokens)
            with patch.object(
                RedisTokenRepository,
                "from_config",
                side_effect=lambda: RedisTokenRepository(
                    Redis.from_url(os.environ["TEST_DELETION_REDIS_URL"])
                ),
            ):
                await worker.run(command.operation_id)
            self.assertEqual((await self.state(command)).state, "deleted")
            self.assertEqual(await client.exists(*removed), 0)
            self.assertEqual(await client.exists(*preserved), len(preserved))
        finally:
            await client.delete(*(removed + preserved))
            await client.aclose()
