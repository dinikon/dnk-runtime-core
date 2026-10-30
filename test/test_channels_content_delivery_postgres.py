"""HTTP → Shared Jobs → настоящий Worker → SQL с контролируемым WooCommerce."""

import asyncio
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from unittest import TestLoader, TestSuite
from unittest.mock import AsyncMock, Mock, patch
from uuid import UUID, uuid4

from sqlalchemy import delete, insert, select, update

from src.modules.channels.application.error import VerificationFailure
from src.modules.channels.infrastructure.content_delivery.jobs import JOB_TYPE
from src.modules.channels.infrastructure.persistence.models.content_delivery import (
    ContentDeliveryModel as D,
)
from src.modules.channels.infrastructure.persistence.models.content_media import (
    ContentMediaModel as M,
)
from src.modules.channels.infrastructure.persistence.models.external_publication import (
    ExternalPublicationModel as P,
)
from src.modules.channels.infrastructure.registry import InstalledPlatforms
from src.modules.channels.presentation.content_delivery.assembly import (
    ContentDeliveryRuntime,
    build_content_delivery_runtime,
)
from src.modules.channels.presentation.content_delivery.depends import (
    get_content_delivery_runtime,
)
from src.modules.channels.presentation.content_delivery.jobs import (
    ChannelsContentDeliveryJobHandler,
)
from src.modules.channels.presentation.content_media.depends import MediaTenantDep
from src.modules.identity.presentation.access.depends import (
    default_authorization_service,
)
from src.modules.shared.domain.jobs.scheduled_job import ScheduledJob
from src.modules.shared.infrastructure.jobs.scheduled_job_model import (
    ScheduledJobModel as J,
)
from src.modules.shared.infrastructure.jobs.sqlalchemy_scheduled_job_repository import (
    SqlAlchemyScheduledJobRepository,
)
from src.modules.shared.infrastructure.persistence.unit_of_work.sqlalchemy import (
    UnitOfWork,
)
from src.modules.shared.infrastructure.time.utc_clock import UtcClock
from src.modules.shared.infrastructure.uuid.uuid7_generator import UUID7Generator
from src.modules.shared.presentation.persistence.depends import UoWDep
from src.modules.tenancy.infrastructure.persistence.tenant_domain import (
    TenantDomainModel,
)
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_connection import (
    bind_tenant_schema,
)
from test.test_channels_content_media_postgres import ContentMediaPostgresTests


class ContentDeliveryPostgresTests(ContentMediaPostgresTests):
    """Сохраняет реальные владельцы, миграции, транзакции, lease и авторизацию HTTP."""

    async def asyncSetUp(self) -> None:
        await super().asyncSetUp()
        self.remote = {
            "id": 101,
            "type": "simple",
            "name": "Old",
            "description": "Old",
            "images": [],
            "sku": "unchanged",
            "regular_price": "15.00",
            "stock_quantity": 7,
            "attributes": [],
        }
        self.puts: list[dict] = []
        self.timeout_after_write = False
        self.worker_authorization = default_authorization_service
        self.entered: asyncio.Event | None = None
        self.release: asyncio.Event | None = None
        self.network_session = None
        self.http = Mock()

        async def send(
            method: str,
            url: str,
            *,
            headers: dict | None = None,
            body: dict | None = None,
        ) -> dict:
            """Моделирует изменение площадки, включая потерю ответа после применения."""
            if self.network_session is not None:
                self.assertFalse(
                    self.network_session.in_transaction(),
                    "Woo API inside SQL transaction",
                )
            self.assertIn("/products/101", url)
            if method == "PUT":
                self.assertIsNotNone(body)
                self.assertLessEqual(set(body), {"name", "description", "images"})
                self.puts.append(body)
                self.remote.update(body)
                if "images" in body:
                    self.remote["images"] = [
                        {"id": image.get("id", 70 + index), "alt": image.get("alt", "")}
                        for index, image in enumerate(body["images"])
                    ]
                if self.entered is not None:
                    self.entered.set()
                    await self.release.wait()
                if self.timeout_after_write:
                    raise VerificationFailure("network_timeout", retryable=True)
            return dict(self.remote)

        self.http.request = AsyncMock(side_effect=send)
        self.platforms = InstalledPlatforms(self.http)

        async def runtime(
            uow: UoWDep, tenant: MediaTenantDep
        ) -> ContentDeliveryRuntime:
            """Подменяет только внешние API/storage, не Commands или SQL."""
            return self.runtime_for(uow, tenant.base_url)

        self.app.dependency_overrides[get_content_delivery_runtime] = runtime
        async with self.engine.begin() as connection:
            await connection.run_sync(
                lambda c: TenantDomainModel.__table__.create(c, checkfirst=True)
            )
            await connection.execute(
                insert(TenantDomainModel).values(
                    id=uuid4(),
                    tenant_id=self.tenant,
                    host="tenant.example",
                    service_type="http",
                    kind="custom",
                    status="active",
                    verification_status="verified",
                    is_primary=True,
                    is_wildcard=False,
                )
            )

    async def asyncTearDown(self) -> None:
        async with self.engine.begin() as connection:
            await connection.execute(
                delete(TenantDomainModel).where(
                    TenantDomainModel.tenant_id == self.tenant
                )
            )
        await super().asyncTearDown()

    def runtime_for(
        self, uow: UnitOfWork, base_url: str = "https://tenant.example"
    ) -> ContentDeliveryRuntime:
        """Создаёт рабочую сборку на той же сессии, без подмены внутренних портов."""
        return build_content_delivery_runtime(
            session=uow.session,
            tenant_id=self.tenant,
            base_url=base_url,
            uow=uow,
            cipher=self.cipher,
            clock=UtcClock(),
            uuid=UUID7Generator(),
            platforms=self.platforms,
            storage=self.storage,
            authorization=default_authorization_service,
        )

    async def request_delivery(
        self, channel: str, group: str, detail: dict, *, status: int = 202
    ) -> dict:
        """Использует fingerprint реально прочитанного preview."""
        preview = await self.call("POST", self.path(channel, group) + "/preview", {})
        return await self.call(
            "POST",
            f"/channels/{channel}/catalog-bindings/{group}/content-deliveries",
            self.version(detail)
            | {"content_fingerprint": preview["content_fingerprint"]},
            status,
        )

    async def claim_delivery(self) -> ScheduledJob:
        """Фиксирует настоящий lease Shared Jobs перед вызовом Worker."""
        async with self.sessions() as session:
            now = datetime.now(UTC)
            jobs = await SqlAlchemyScheduledJobRepository(session).claim_due_jobs(
                limit=100,
                now=now,
                locked_until=now + timedelta(minutes=5),
                lock_token=str(uuid4()),
            )
            await session.commit()
        self.claimed_jobs = [
            job
            for job in jobs
            if job.job_type == JOB_TYPE and job.tenant_id == self.tenant
        ]
        return self.claimed_jobs[0]

    async def execute_job(self, job: ScheduledJob, *, done: bool = True) -> None:
        """Проверяет внешний вызов между завершёнными транзакциями настоящего Worker."""
        worker = ChannelsContentDeliveryJobHandler(
            self.sessions,
            platforms=self.platforms,
            cipher=self.cipher,
            storage=self.storage,
            authorization=self.worker_authorization,
        )
        original = worker._runtime

        def runtime(
            uow: UnitOfWork, tenant_id: UUID, base_url: str
        ) -> ContentDeliveryRuntime:
            self.network_session = uow.session
            self.storage.before_open = lambda: self.assertFalse(
                uow.session.in_transaction()
            )
            return original(uow, tenant_id, base_url)

        with patch.object(worker, "_runtime", runtime):
            await worker.handle(job)
        if done:
            async with self.sessions() as session:
                await SqlAlchemyScheduledJobRepository(session).mark_done(
                    job_id=job.id,
                    lock_token=job.lock_token,
                    completed_at=datetime.now(UTC),
                )
                await session.commit()

    async def results(self, channel: str, group: str) -> list[dict]:
        """Читает публичные результаты целей после завершения задания."""
        return (
            await self.call(
                "GET",
                f"/channels/{channel}/catalog-bindings/{group}/content-deliveries",
            )
        )["items"]

    async def test_full_http_worker_flow_and_repeat_reuses_media(self) -> None:
        channel, group, _, detail, _ = await self.media_fixture("woocommerce")
        raw_before = await self.rows(P)
        accepted = await self.request_delivery(channel, group, detail)
        self.assertEqual(accepted["items"][0]["status"], "queued")
        job = await self.claim_delivery()
        await self.execute_job(job)
        result = (await self.results(channel, group))[0]
        self.assertEqual(result["status"], "succeeded")
        self.assertEqual(result["applied_generation"], 1)
        self.assertEqual(set(result["confirmed_fields"]), {"title", "body", "gallery"})
        self.assertEqual(self.remote["name"], "Title uk")
        self.assertEqual(
            [
                self.remote[k]
                for k in ("sku", "regular_price", "stock_quantity", "attributes")
            ],
            ["unchanged", "15.00", 7, []],
        )
        self.assertEqual(await self.rows(P), raw_before)
        rows = await self.rows(D)
        self.assertNotIn(b"token=", rows[0]["prepared_request_encrypted"])
        self.assertIn(
            b"token=", self.cipher.decrypt(rows[0]["prepared_request_encrypted"])
        )
        self.assertEqual(
            [
                row["remote_media_id"]
                for row in sorted(
                    await self.rows(M), key=lambda row: row["remote_media_id"]
                )
            ],
            ["70", "71"],
        )
        self.remote["name"] = "Manually changed"
        await self.request_delivery(channel, group, detail)
        await self.execute_job(await self.claim_delivery())
        self.assertEqual(
            (await self.results(channel, group))[0]["applied_generation"], 2
        )
        self.assertEqual(len(self.puts), 2)
        self.assertTrue(
            all(
                "id" in image and "src" not in image for image in self.puts[1]["images"]
            )
        )

    async def test_duplicate_start_stale_preview_and_disable_cancel(self) -> None:
        channel, group, root, detail, _ = await self.media_fixture("woocommerce")
        preview = await self.call("POST", self.path(channel, group) + "/preview", {})
        path = f"/channels/{channel}/catalog-bindings/{group}/content-deliveries"
        body = self.version(detail) | {
            "content_fingerprint": preview["content_fingerprint"]
        }
        await asyncio.gather(
            self.call("POST", path, body, 202), self.call("POST", path, body, 202)
        )
        self.assertEqual((await self.rows(D))[0]["requested_generation"], 1)
        self.assertEqual(
            len([j for j in await self.rows(J) if j["job_type"] == JOB_TYPE]), 1
        )
        await self.set_content(root, "uk", "Changed Catalog")
        error = await self.call("POST", path, body, 409)
        self.assertEqual(error["detail"]["code"], "content_preview_changed")
        await self.call(
            "POST", self.path(channel, group) + "/disable", self.version(detail)
        )
        self.assertEqual((await self.results(channel, group))[0]["status"], "cancelled")
        await self.execute_job(await self.claim_delivery())
        self.http.request.assert_not_awaited()

    async def test_timeout_upload_requires_reconciliation_and_never_reuploads(
        self,
    ) -> None:
        channel, group, _, detail, _ = await self.media_fixture("woocommerce")
        await self.request_delivery(channel, group, detail)
        job = await self.claim_delivery()
        self.timeout_after_write = True
        await self.execute_job(job, done=False)
        self.assertEqual((await self.results(channel, group))[0]["status"], "unknown")
        self.timeout_after_write = False
        await self.execute_job(job)
        row = (await self.results(channel, group))[0]
        self.assertEqual(row["status"], "unknown")
        self.assertEqual(len(self.puts), 1)
        await self.call(
            "POST",
            f"/channels/{channel}/catalog-bindings/{group}/content-deliveries/{row['publication_id']}/reconcile",
            {"expected_revision": row["revision"]},
            202,
        )
        await self.execute_job(await self.claim_delivery())
        self.assertEqual((await self.results(channel, group))[0]["status"], "unknown")
        self.assertEqual(len(self.puts), 1)

    async def test_known_media_timeout_is_confirmed_by_read_and_lost_lease_is_fenced(
        self,
    ) -> None:
        channel, group, _, detail, _ = await self.media_fixture("woocommerce")
        await self.request_delivery(channel, group, detail)
        await self.execute_job(await self.claim_delivery())
        self.remote["name"] = "Old again"
        await self.request_delivery(channel, group, detail)
        job = await self.claim_delivery()
        self.timeout_after_write = True
        await self.execute_job(job, done=False)
        self.assertEqual((await self.results(channel, group))[0]["status"], "unknown")
        self.timeout_after_write = False
        await self.execute_job(job)
        self.assertEqual((await self.results(channel, group))[0]["status"], "succeeded")
        self.assertEqual(len(self.puts), 2)
        await self.request_delivery(channel, group, detail)
        job = await self.claim_delivery()
        await self.execute_job(replace(job, lock_token="wrong-lease"), done=False)
        self.assertEqual((await self.results(channel, group))[0]["status"], "queued")
        self.assertEqual(len(self.puts), 2)

    async def test_catalog_change_during_api_keeps_applied_fact_without_automatic_new_send(
        self,
    ) -> None:
        channel, group, root, detail, _ = await self.media_fixture("woocommerce")
        await self.request_delivery(channel, group, detail)
        self.entered, self.release = asyncio.Event(), asyncio.Event()
        running = asyncio.create_task(self.execute_job(await self.claim_delivery()))
        await asyncio.wait_for(self.entered.wait(), 10)
        try:
            await self.set_content(root, "uk", "New Catalog")
        finally:
            self.release.set()
        await asyncio.wait_for(running, 10)
        row = (await self.results(channel, group))[0]
        preview = await self.call("POST", self.path(channel, group) + "/preview", {})
        self.assertEqual(row["status"], "succeeded")
        self.assertNotEqual(row["content_fingerprint"], preview["content_fingerprint"])
        self.assertEqual(len(self.puts), 1)

    async def test_lost_lease_during_put_drops_result_and_recovery_only_reads(
        self,
    ) -> None:
        """Новый lease не допускает применения старого ответа или второго PUT."""
        channel, group, _, detail, _ = await self.media_fixture("woocommerce")
        await self.request_delivery(channel, group, detail)
        job = await self.claim_delivery()
        self.entered, self.release = asyncio.Event(), asyncio.Event()
        running = asyncio.create_task(self.execute_job(job, done=False))
        await asyncio.wait_for(self.entered.wait(), 10)
        try:
            async with self.sessions() as session:
                await session.execute(
                    update(J).where(J.id == job.id).values(lock_token="new-lease")
                )
                await session.commit()
        finally:
            self.release.set()
        await asyncio.wait_for(running, 10)
        self.assertEqual((await self.results(channel, group))[0]["status"], "in_flight")
        await self.execute_job(replace(job, lock_token="new-lease"))
        self.assertEqual((await self.results(channel, group))[0]["status"], "unknown")
        self.assertEqual(len(self.puts), 1)

    async def test_request_waiting_during_api_does_not_deadlock_catalog_barrier(
        self,
    ) -> None:
        """Редактор держит Catalog и ждёт Channel; apply не захватывает Catalog повторно."""
        channel, group, root, detail, _ = await self.media_fixture("woocommerce")
        await self.request_delivery(channel, group, detail)
        self.entered, self.release = asyncio.Event(), asyncio.Event()
        running = asyncio.create_task(self.execute_job(await self.claim_delivery()))
        await asyncio.wait_for(self.entered.wait(), 10)
        requesting = None
        try:
            await self.set_content(root, "uk", "Next explicit generation")
            requesting = asyncio.create_task(
                self.request_delivery(channel, group, detail)
            )
            await asyncio.sleep(0.05)
            self.assertFalse(requesting.done())
        finally:
            self.release.set()
        results = await asyncio.wait_for(asyncio.gather(running, requesting), 10)
        self.assertEqual(results[1]["items"][0]["requested_generation"], 2)
        await self.execute_job(await self.claim_delivery())
        self.assertEqual(self.remote["name"], "Next explicit generation")
        self.assertEqual(
            (await self.results(channel, group))[0]["applied_generation"], 2
        )

    async def test_container_and_variations_have_separate_targets_and_partial_results(
        self,
    ) -> None:
        """Одна отклонённая вариация не отменяет подтверждённые соседние цели."""
        root, positions = await self.catalog(variable=True)
        await self.set_content(root, "uk", "Container name")
        channel, publications = await self.source("woocommerce", variable=True)
        _, extra = await self.source("woocommerce", existing_channel=channel)
        publications += extra
        async with self.sessions() as session:
            await bind_tenant_schema(
                await session.connection(), self.tenant, self.naming
            )
            for index, identifier in enumerate(publications):
                await session.execute(
                    update(P)
                    .where(P.id == UUID(identifier))
                    .values(
                        external_id=str(101 if index == 0 else 200 + index),
                        kind="variable" if index == 0 else "variant",
                        parent_id=None if index == 0 else UUID(publications[0]),
                    )
                )
            await session.commit()
        group = await self.group(
            channel,
            root,
            positions,
            publications[1:],
            "VARIABLE_TO_VARIABLE",
            publications[0],
        )
        path = self.path(channel, group)
        detail = await self.call("GET", path)
        detail = await self.call("PUT", path, self.version(detail) | {"overrides": {}})
        await self.verified(channel)
        detail = await self.call("POST", path + "/enable", self.version(detail))
        remote = {
            101: {
                "id": 101,
                "type": "variable",
                "name": "Old",
                "description": "Old",
                "images": [],
            },
            201: {
                "id": 201,
                "parent_id": 101,
                "type": "variation",
                "description": "Old",
                "image": None,
            },
            202: {
                "id": 202,
                "parent_id": 101,
                "type": "variation",
                "description": "Old",
                "image": None,
            },
        }
        calls = []

        async def send(
            method: str,
            url: str,
            *,
            headers: dict | None = None,
            body: dict | None = None,
        ) -> dict:
            """Различает адреса контейнера и вариаций без внешних сетевых сервисов."""
            self.assertFalse(self.network_session.in_transaction())
            identifier = int(url.split("?")[0].rsplit("/", 1)[1])
            if identifier == 201:
                raise VerificationFailure("permission_missing")
            if method == "PUT":
                calls.append((url, body))
                remote[identifier].update(body)
                if body.get("image") == {"id": 0}:
                    remote[identifier]["image"] = None
            return remote[identifier]

        self.http.request.side_effect = send
        accepted = await self.request_delivery(channel, group, detail)
        self.assertEqual(len(accepted["items"]), 3)
        await self.claim_delivery()
        jobs = sorted(
            self.claimed_jobs,
            key=lambda job: job.payload["publication_id"] != publications[0],
        )
        for job in jobs:
            await self.execute_job(job)
        rows = await self.results(channel, group)
        self.assertEqual(
            sorted(row["status"] for row in rows), ["failed", "succeeded", "succeeded"]
        )
        self.assertEqual(remote[101]["name"], "Container name")
        self.assertTrue(any("/products/101/variations/202" in url for url, _ in calls))
        for url, body in calls:
            self.assertLessEqual(
                set(body),
                (
                    {"description", "image"}
                    if "/variations/" in url
                    else {"name", "description", "images"}
                ),
            )

        remote[101]["type"] = "simple"
        calls.clear()
        self.http.request.reset_mock()
        await self.request_delivery(channel, group, detail)
        await self.claim_delivery()
        for job in sorted(
            self.claimed_jobs,
            key=lambda job: job.payload["publication_id"] != publications[0],
        ):
            await self.execute_job(job)
        rows = await self.results(channel, group)
        self.assertEqual(
            sorted(row["status"] for row in rows), ["blocked", "blocked", "failed"]
        )
        self.assertEqual(calls, [])
        self.assertEqual(self.http.request.await_count, 1)

    async def test_worker_rechecks_actor_permissions_before_write_and_reconciliation(
        self,
    ) -> None:
        """Отзыв права после HTTP не выполняет PUT; сверка тоже использует политику Worker."""
        channel, group, _, detail, _ = await self.media_fixture("woocommerce")
        await self.request_delivery(channel, group, detail)
        deny = Mock()
        deny.can = AsyncMock(return_value=False)
        self.worker_authorization = deny
        await self.execute_job(await self.claim_delivery())
        self.assertEqual((await self.results(channel, group))[0]["status"], "blocked")
        self.http.request.assert_not_awaited()
        self.worker_authorization = default_authorization_service
        await self.request_delivery(channel, group, detail)
        self.timeout_after_write = True
        await self.execute_job(await self.claim_delivery())
        row = (await self.results(channel, group))[0]
        self.assertEqual(row["status"], "unknown")
        await self.call(
            "POST",
            f"/channels/{channel}/catalog-bindings/{group}/content-deliveries/{row['publication_id']}/reconcile",
            {"expected_revision": row["revision"]},
            202,
        )
        self.worker_authorization = deny
        self.http.request.reset_mock()
        await self.execute_job(await self.claim_delivery())
        self.http.request.assert_not_awaited()
        self.assertEqual((await self.results(channel, group))[0]["status"], "unknown")

    async def test_schedule_failure_rolls_back_new_generation_and_http_requires_csrf(
        self,
    ) -> None:
        """Нельзя сохранить доставку без задания или запустить её без CSRF."""
        channel, group, _, detail, _ = await self.media_fixture("woocommerce")
        from src.modules.channels.infrastructure.content_delivery.jobs import (
            SharedContentDeliveryJobs,
        )

        with patch.object(
            SharedContentDeliveryJobs,
            "schedule",
            AsyncMock(side_effect=RuntimeError("schedule failed")),
        ):
            with self.assertRaises(RuntimeError):
                await self.request_delivery(channel, group, detail)
        self.assertEqual(await self.rows(D), [])
        self.assertEqual(await self.rows(M), [])
        preview = await self.call("POST", self.path(channel, group) + "/preview", {})
        response = await self.client.post(
            f"/api/console/channels/{channel}/catalog-bindings/{group}/content-deliveries",
            json=self.version(detail)
            | {"content_fingerprint": preview["content_fingerprint"]},
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(await self.rows(D), [])


def load_tests(loader: TestLoader, tests: TestSuite, pattern: str | None) -> TestSuite:
    """Не запускает повторно унаследованные fixtures и media-сценарии."""
    return TestSuite(
        ContentDeliveryPostgresTests(name)
        for name in ContentDeliveryPostgresTests.__dict__
        if name.startswith("test_")
    )
