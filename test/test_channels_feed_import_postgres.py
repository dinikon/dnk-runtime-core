"""HTTP → ContentFeed → Shared Jobs → worker → API Prom с настоящими транзакциями."""

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from unittest import TestLoader, TestSuite
from unittest.mock import Mock, AsyncMock, patch
from uuid import UUID, uuid4
from xml.etree import ElementTree as ET
import asyncio
import json

from sqlalchemy import insert, update, delete, select

from src.modules.channels.application.error import VerificationFailure
from src.modules.channels.application.content_feed.service.imports import FeedImports
from src.modules.channels.infrastructure.content_feed.jobs import JOB_TYPE
from src.modules.channels.infrastructure.content_feed.source import HttpsFeedSource
from src.modules.channels.infrastructure.persistence.models.content_feed import (
    ContentFeedModel as F,
)
from src.modules.channels.infrastructure.persistence.models.external_publication import (
    ExternalPublicationModel as P,
)
from src.modules.channels.infrastructure.registry import InstalledPlatforms
from src.modules.channels.presentation.content_feed.assembly import (
    build_content_feed_runtime,
    ContentFeedRuntime,
)
from src.modules.channels.presentation.content_feed.depends import (
    get_content_feed_runtime,
)
from src.modules.channels.presentation.content_feed.jobs import (
    ChannelsFeedImportJobHandler,
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
    TenantDomainModel as D,
)
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_connection import (
    bind_tenant_schema,
)
from test.test_channels_content_feed_postgres import ContentFeedPostgresTests


class FeedImportPostgresTests(ContentFeedPostgresTests):
    async def asyncSetUp(self) -> None:
        """Подменяет только HTTP Prom и исходника; все владельцы данных остаются настоящими."""
        await super().asyncSetUp()
        self.network_session = None
        self.remote = {
            "id": 99,
            "external_id": "001",
            "name": "Old",
            "description": "Old body",
            "name_multilang": {},
            "description_multilang": {},
            "images": [],
            "price": 99,
            "quantity_in_stock": 17,
            "sku": "platform-sku",
        }
        self.unmatched = {
            "id": 100,
            "external_id": "002",
            "name": "Unmatched",
            "images": [],
        }
        self.posts = []
        self.api_calls = []
        self.post_timeout = False
        self.report_pending = False
        self.provider_status = "SUCCESS"
        self.created_count = 0
        self.post_entered = None
        self.post_release = None
        self.authorization = default_authorization_service
        self.http = Mock()

        async def request(
            method: str,
            url: str,
            *,
            headers: dict | None = None,
            body: dict | None = None,
        ) -> dict:
            """Проверяет границу транзакции и моделирует скачивание настоящего XML endpoint."""
            if self.network_session is not None:
                self.assertFalse(
                    self.network_session.in_transaction(),
                    "Prom API inside SQL transaction",
                )
            self.api_calls.append((method, url))
            if method == "POST":
                self.posts.append(body)
                response = await self.client.get(body["url"])
                self.assertEqual(response.status_code, 200, response.text)
                offer = ET.fromstring(response.content).find("./shop/offers/offer")
                self.remote["name"] = offer.findtext("name")
                self.remote["description"] = offer.findtext("description")
                self.remote["name_multilang"] = {
                    "uk": offer.findtext("name_ua"),
                    "ru": offer.findtext("name"),
                }
                self.remote["description_multilang"] = {
                    "uk": offer.findtext("description_ua"),
                    "ru": offer.findtext("description"),
                }
                self.remote["images"] = [
                    {
                        "id": 501 + i,
                        "url": f"https://images.prom.ua/{501+i}_w200_h200_photo.png",
                    }
                    for i, node in enumerate(offer.findall("picture"))
                ]
                if self.post_entered is not None:
                    self.post_entered.set()
                    await self.post_release.wait()
                if self.post_timeout:
                    raise VerificationFailure("network_timeout", retryable=True)
                return {"status": "success", "id": "77"}
            if "/products/import/status/" in url:
                return (
                    {"status": "RUNNING"}
                    if self.report_pending
                    else {
                        "status": self.provider_status,
                        "total": 2,
                        "updated": 1,
                        "created": self.created_count,
                        "with_errors_count": (
                            0 if self.provider_status == "SUCCESS" else 1
                        ),
                        "not_changed": 1,
                    }
                )
            if "/products/list" in url:
                return {"products": [dict(self.remote), dict(self.unmatched)]}
            return {"product": dict(self.remote)}

        self.http.request = AsyncMock(side_effect=request)
        self.platforms = InstalledPlatforms(self.http)

        async def runtime(uow: UoWDep, tenant: MediaTenantDep) -> ContentFeedRuntime:
            """Собирает те же сценарии для HTTP, что используются в worker."""
            return self.runtime_for(uow, tenant.base_url)

        self.app.dependency_overrides[get_content_feed_runtime] = runtime
        async with self.engine.begin() as connection:
            await connection.run_sync(lambda c: D.__table__.create(c, checkfirst=True))
            await connection.execute(
                insert(D).values(
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
        """Удаляет только домен и схемы текущего теста."""
        async with self.engine.begin() as connection:
            await connection.execute(delete(D).where(D.tenant_id == self.tenant))
        await super().asyncTearDown()

    async def source(
        self,
        platform: str = "prom",
        variable: bool = False,
        existing_channel: str | None = None,
    ) -> tuple[str, list[str]]:
        """Фиксирует нативный ID до создания сопоставления, не меняя его адресата позже."""
        channel, pubs = await super().source(platform, variable, existing_channel)
        async with self.sessions() as session:
            await bind_tenant_schema(
                await session.connection(), self.tenant, self.naming
            )
            for index, identifier in enumerate(pubs):
                await session.execute(
                    update(P)
                    .where(P.id == UUID(identifier))
                    .values(external_id=str(99 + index))
                )
            await session.commit()
        return channel, pubs

    def runtime_for(
        self, uow: UnitOfWork, base_url: str = "https://tenant.example"
    ) -> ContentFeedRuntime:
        """Связывает реальный UoW с контролируемым внешним транспортом."""
        self.network_session = uow.session

        async def fetch(url: str) -> bytes:
            """Не открывает исходник при активной SQL-транзакции."""
            self.assertFalse(uow.session.in_transaction())
            return self.xml

        return build_content_feed_runtime(
            session=uow.session,
            tenant_id=self.tenant,
            base_url=base_url,
            uow=uow,
            cipher=self.cipher,
            clock=UtcClock(),
            uuid=UUID7Generator(),
            platforms=self.platforms,
            storage=self.storage,
            authorization=self.authorization,
            source=Mock(
                validate_url=HttpsFeedSource().validate_url,
                fetch=AsyncMock(side_effect=fetch),
            ),
        )

    async def operation(self, channel: str, value: dict) -> dict:
        """Читает только локальную проекцию, не вызывает Prom из Console polling."""
        return (
            await self.call("GET", self.feed_path(channel, value) + "/imports/current")
        )["operation"]

    async def start_import(
        self,
        channel: str,
        value: dict,
        *,
        request_id: str | None = None,
        status: int = 202,
    ) -> dict:
        """Передаёт два счётчика ревизий и стабильный request_id."""
        operation = await self.operation(channel, value)
        response = await self.call(
            "POST",
            self.feed_path(channel, value) + "/imports",
            {
                "expected_revision": value["revision"],
                "expected_delivery_revision": operation["revision"],
                "request_id": request_id or str(uuid4()),
                "force_update": False,
            },
            status,
        )
        return response["operation"] if status == 202 else response

    async def claim_job(self) -> ScheduledJob:
        """Claim использует настоящий repository и действующую lease Shared Jobs."""
        async with self.sessions() as session:
            await session.execute(
                update(J)
                .where(
                    J.tenant_id == self.tenant,
                    J.job_type == JOB_TYPE,
                    J.status == "scheduled",
                )
                .values(run_at=datetime.now(UTC) - timedelta(seconds=1))
            )
            now = datetime.now(UTC)
            jobs = await SqlAlchemyScheduledJobRepository(session).claim_due_jobs(
                limit=100,
                now=now,
                locked_until=now + timedelta(minutes=5),
                lock_token=str(uuid4()),
            )
            await session.commit()
        selected = [
            job
            for job in jobs
            if job.job_type == JOB_TYPE and job.tenant_id == self.tenant
        ]
        self.assertEqual(len(selected), 1)
        return selected[0]

    async def execute(self, job: ScheduledJob, *, done: bool = True) -> None:
        """Запускает настоящий job handler со сборкой этапов и шифрованием."""
        worker = ChannelsFeedImportJobHandler(
            self.sessions,
            platforms=self.platforms,
            cipher=self.cipher,
            storage=self.storage,
            authorization=self.authorization,
        )

        def runtime(
            uow: UnitOfWork, *, tenant_id: UUID, base_url: str
        ) -> ContentFeedRuntime:
            """Подменяет только внешние источники, не Application или SQL."""
            return self.runtime_for(uow, base_url)

        with patch.object(worker, "_runtime", runtime):
            await asyncio.wait_for(worker.handle(job), timeout=30)
        if done:
            async with self.sessions() as session:
                await SqlAlchemyScheduledJobRepository(session).mark_done(
                    job_id=job.id,
                    lock_token=job.lock_token,
                    completed_at=datetime.now(UTC),
                )
                await session.commit()

    async def test_full_path_fetches_xml_once_and_confirms_fields_without_price_changes(
        self,
    ) -> None:
        """Проверяет живой endpoint между POST, отчётом и отдельным чтением товара."""
        channel, _, _, value, _ = await self.setup_feed()
        value = await self.enable_feed(channel, value)
        revision = value["revision"]
        source_cipher = (await self.rows(F))[0]["source_url_encrypted"]
        request_id = str(uuid4())
        queued = await self.start_import(channel, value, request_id=request_id)
        same = await self.start_import(channel, value, request_id=request_id)
        self.assertEqual(same, queued)
        await self.execute(await self.claim_job())
        processing = await self.operation(channel, value)
        self.assertEqual(
            (processing["phase"], processing["external_import_id"]),
            ("processing", "77"),
        )
        self.assertEqual(len(self.posts), 1)
        self.assertEqual(
            set(self.posts[0]["updated_fields"]),
            {"name", "description", "name_ua", "description_ua", "images_urls"},
        )
        self.assertEqual(self.posts[0]["mark_missing_product_as"], "none")
        await self.execute(await self.claim_job())
        self.assertEqual((await self.operation(channel, value))["phase"], "verifying")
        await self.execute(await self.claim_job())
        final = await self.operation(channel, value)
        self.assertEqual(final["phase"], "completed")
        self.assertIsNone(final["error_code"])
        self.assertTrue(
            all(
                f["status"] == "confirmed"
                for v in final["verification"]
                for f in v["fields"]
            )
        )
        current = (await self.call("GET", self.feed_path(channel, value)))["feed"]
        self.assertEqual(current["revision"], revision)
        stored = (await self.rows(F))[0]
        self.assertEqual(stored["source_url_encrypted"], source_cipher)
        token = value["public_url"].split("token=")[1]
        self.assertNotIn(token, json.dumps(stored["delivery_state"]))
        self.assertNotIn(token.encode(), stored["delivery_request_encrypted"])
        self.assertEqual(
            (
                self.remote["price"],
                self.remote["quantity_in_stock"],
                self.remote["sku"],
            ),
            (99, 17, "platform-sku"),
        )
        jobs = await self.rows(J)
        self.assertNotIn(token, json.dumps([job["payload"] for job in jobs]))
        count = len(self.api_calls)
        await self.operation(channel, value)
        self.assertEqual(len(self.api_calls), count)

    async def test_timeout_does_not_post_again_and_manual_id_can_finish_verification(
        self,
    ) -> None:
        """Неизвестное принятие требует ручного ID, повторный worker не отправляет фид."""
        channel, _, _, value, _ = await self.setup_feed()
        value = await self.enable_feed(channel, value)
        await self.start_import(channel, value)
        self.post_timeout = True
        job = await self.claim_job()
        await self.execute(job)
        unknown = await self.operation(channel, value)
        self.assertEqual(unknown["phase"], "unknown")
        self.assertFalse(unknown["can_start"])
        await self.execute(job, done=False)
        self.assertEqual(len(self.posts), 1)
        await self.start_import(channel, value, status=409)
        attached = await self.call(
            "POST",
            self.feed_path(channel, value) + "/imports/current/attach",
            {
                "expected_revision": value["revision"],
                "expected_delivery_revision": unknown["revision"],
                "external_id": "77",
            },
        )
        self.assertEqual(attached["operation"]["phase"], "verifying")
        self.assertEqual(
            attached["operation"]["manual_resolution"], "import_id_attached"
        )
        await self.execute(await self.claim_job())
        self.assertEqual((await self.operation(channel, value))["phase"], "completed")
        self.assertEqual(len(self.posts), 1)

    async def test_crash_after_post_before_commit_recovers_to_unknown(self) -> None:
        """Падение после внешнего эффекта не превращается во второй POST."""
        channel, _, _, value, _ = await self.setup_feed()
        value = await self.enable_feed(channel, value)
        await self.start_import(channel, value)
        job = await self.claim_job()
        with patch.object(
            FeedImports,
            "apply_submission",
            AsyncMock(side_effect=RuntimeError("crash")),
        ):
            with self.assertRaises(RuntimeError):
                await self.execute(job, done=False)
        self.assertEqual((await self.operation(channel, value))["phase"], "submitting")
        await self.execute(job)
        self.assertEqual((await self.operation(channel, value))["phase"], "unknown")
        self.assertEqual(len(self.posts), 1)

    async def test_partial_report_and_gallery_have_independent_truthful_results(
        self,
    ) -> None:
        """Отчёт SUCCESS не подтверждает содержимое новых CDN-фотографий."""
        channel, _, _, value, _ = await self.setup_feed(media=True)
        value = await self.enable_feed(channel, value)
        await self.start_import(channel, value)
        await self.execute(await self.claim_job())
        await self.execute(await self.claim_job())
        await self.execute(await self.claim_job())
        result = await self.operation(channel, value)
        self.assertEqual(result["report"]["status"], "SUCCESS")
        self.assertEqual(
            result["verification"][0]["fields"][-1]["status"], "unconfirmed"
        )
        self.assertEqual(result["error_code"], "feed_import_content_unconfirmed")
        self.provider_status = "PARTIAL"
        await self.start_import(channel, value)
        await self.execute(await self.claim_job())
        await self.execute(await self.claim_job())
        await self.execute(await self.claim_job())
        result = await self.operation(channel, value)
        self.assertEqual(result["report"]["status"], "PARTIAL")
        self.assertEqual(result["error_code"], "feed_import_report_requires_attention")

    async def test_changed_catalog_marks_old_results_obsolete(self) -> None:
        """Динамический endpoint не фиксирует версию контента между скачиванием и сверкой."""
        channel, _, root, value, _ = await self.setup_feed()
        value = await self.enable_feed(channel, value)
        await self.start_import(channel, value)
        await self.execute(await self.claim_job())
        await self.set_content(root, "ru", "Changed after submit")
        await self.execute(await self.claim_job())
        await self.execute(await self.claim_job())
        result = await self.operation(channel, value)
        self.assertEqual(result["error_code"], "feed_import_context_changed")
        self.assertTrue(
            all(
                f["status"] == "obsolete"
                for v in result["verification"]
                for f in v["fields"]
            )
        )

    async def test_pending_deadline_and_resume_only_read_known_id(self) -> None:
        """Неописанный промежуточный статус ограниченно опрашивается и не выдаётся за успех."""
        channel, _, _, value, _ = await self.setup_feed()
        value = await self.enable_feed(channel, value)
        await self.start_import(channel, value)
        await self.execute(await self.claim_job())
        self.report_pending = True
        await self.execute(await self.claim_job())
        result = await self.operation(channel, value)
        self.assertEqual(result["phase"], "processing")
        self.assertIsNone(result["report"])
        async with self.sessions() as session:
            await bind_tenant_schema(
                await session.connection(), self.tenant, self.naming
            )
            row = (await session.execute(select(F.__table__))).mappings().one()
            data = dict(row["delivery_state"])
            data["tracking_deadline"] = data["requested_at"]
            await session.execute(update(F).values(delivery_state=data))
            await session.commit()
        await self.execute(await self.claim_job())
        result = await self.operation(channel, value)
        self.assertEqual(result["phase"], "needs_attention")
        self.assertTrue(result["can_resume"])
        self.report_pending = False
        await self.call(
            "POST",
            self.feed_path(channel, value) + "/imports/current/resume",
            {
                "expected_revision": value["revision"],
                "expected_delivery_revision": result["revision"],
            },
        )
        await self.execute(await self.claim_job())
        await self.execute(await self.claim_job())
        self.assertEqual((await self.operation(channel, value))["phase"], "completed")
        self.assertEqual(len(self.posts), 1)

    async def test_stale_job_and_active_delete_guard_and_emergency_disable(
        self,
    ) -> None:
        """Lease, операция и источник проверяются до POST; отключение остаётся доступным."""
        channel, _, _, value, _ = await self.setup_feed()
        value = await self.enable_feed(channel, value)
        await self.start_import(channel, value)
        job = await self.claim_job()
        await self.execute(replace(job, lock_token="wrong"), done=False)
        self.assertEqual(len(self.posts), 0)
        await self.call(
            "PUT",
            self.feed_path(channel, value),
            {
                "expected_revision": value["revision"],
                "source_url": "https://supplier.example/new.xml",
            },
            409,
        )
        detail = await self.call("GET", f"/channels/{channel}")
        await self.call(
            "DELETE",
            f'/channels/{channel}?expected_revision={detail["revision"]}',
            status=409,
        )
        await self.call(
            "DELETE",
            self.feed_path(channel, value) + f'?expected_revision={value["revision"]}',
            status=409,
        )
        await self.call(
            "POST",
            self.feed_path(channel, value) + "/disable",
            {"expected_revision": value["revision"]},
        )
        await self.execute(job)
        self.assertEqual((await self.operation(channel, value))["phase"], "failed")
        self.assertEqual(len(self.posts), 0)

    async def test_explicit_manual_resolution_and_csrf_are_required(self) -> None:
        """Ручное разрешение не вызывает API и не создаёт новое задание отправки."""
        channel, _, _, value, _ = await self.setup_feed()
        value = await self.enable_feed(channel, value)
        await self.start_import(channel, value)
        self.post_timeout = True
        await self.execute(await self.claim_job())
        state = await self.operation(channel, value)
        path = self.feed_path(channel, value) + "/imports/current/resolve"
        body = {
            "expected_revision": value["revision"],
            "expected_delivery_revision": state["revision"],
            "confirm_not_submitted": True,
        }
        response = await self.client.post("/api/console" + path, json=body)
        self.assertEqual(response.status_code, 403)
        await self.call("POST", path, body | {"confirm_not_submitted": False}, 422)
        result = await self.call("POST", path, body)
        self.assertEqual(result["operation"]["phase"], "resolved")
        self.assertEqual(len(self.posts), 1)
        self.assertTrue(result["operation"]["can_start"])

    async def test_disable_during_post_keeps_accepted_external_id(self) -> None:
        """Аварийное выключение не стирает факт уже принятой ссылки."""
        channel, _, _, value, _ = await self.setup_feed()
        value = await self.enable_feed(channel, value)
        await self.start_import(channel, value)
        self.post_entered, self.post_release = asyncio.Event(), asyncio.Event()
        task = asyncio.create_task(self.execute(await self.claim_job()))
        try:
            await asyncio.wait_for(self.post_entered.wait(), timeout=10)
            await self.call(
                "POST",
                self.feed_path(channel, value) + "/disable",
                {"expected_revision": value["revision"]},
            )
        finally:
            self.post_release.set()
            await task
        state = await self.operation(channel, value)
        self.assertEqual(
            (state["phase"], state["external_import_id"]), ("processing", "77")
        )
        await self.execute(await self.claim_job())
        await self.execute(await self.claim_job())
        self.assertEqual(
            (await self.operation(channel, value))["error_code"],
            "feed_import_context_changed",
        )
        self.assertEqual(len(self.posts), 1)

    async def test_lost_lease_after_post_never_repeats_submission(self) -> None:
        """Устаревший worker не применяет ответ, новый владелец фиксирует unknown."""
        channel, _, _, value, _ = await self.setup_feed()
        value = await self.enable_feed(channel, value)
        await self.start_import(channel, value)
        job = await self.claim_job()
        self.post_entered, self.post_release = asyncio.Event(), asyncio.Event()
        task = asyncio.create_task(self.execute(job, done=False))
        token = str(uuid4())
        try:
            await asyncio.wait_for(self.post_entered.wait(), timeout=10)
            async with self.sessions() as session:
                await session.execute(
                    update(J).where(J.id == job.id).values(lock_token=token)
                )
                await session.commit()
        finally:
            self.post_release.set()
            await task
        self.assertEqual((await self.operation(channel, value))["phase"], "submitting")
        await self.execute(replace(job, lock_token=token))
        self.assertEqual((await self.operation(channel, value))["phase"], "unknown")
        self.assertEqual(len(self.posts), 1)

    async def test_new_source_offer_fails_preflight_before_post(self) -> None:
        """Полный исходник не должен незаметно создать неизвестный товар на площадке."""
        channel, _, _, value, _ = await self.setup_feed()
        value = await self.enable_feed(channel, value)
        await self.start_import(channel, value)
        self.xml = self.xml.replace(
            b"</offers>",
            b'<offer id="003"><name>New</name><categoryId>1</categoryId></offer></offers>',
        )
        await self.execute(await self.claim_job())
        state = await self.operation(channel, value)
        self.assertEqual(
            (state["phase"], state["error_code"]),
            ("failed", "feed_import_would_create_product"),
        )
        self.assertEqual(self.posts, [])

    async def test_revoked_file_rights_pause_verification(self) -> None:
        """Отозванный доступ к Files не позволяет записать подтверждение галереи."""
        channel, _, _, value, _ = await self.setup_feed(media=True)
        value = await self.enable_feed(channel, value)
        await self.start_import(channel, value)
        await self.execute(await self.claim_job())
        await self.execute(await self.claim_job())

        async def can(**request: object) -> bool:
            """Сохраняет доступ к каналу, отзывает только чтение Files."""
            return request["action"] != "files.read"

        self.authorization = Mock(can=AsyncMock(side_effect=can))
        await self.execute(await self.claim_job())
        state = await self.operation(channel, value)
        self.assertEqual(
            (state["phase"], state["error_code"]),
            ("needs_attention", "feed_file_forbidden"),
        )
        self.assertEqual(state["verification"], [])


def load_tests(loader: TestLoader, tests: TestSuite, pattern: str | None) -> TestSuite:
    """Запускает новые сценарии без повторения унаследованных тестов."""
    return TestSuite(
        FeedImportPostgresTests(name)
        for name in FeedImportPostgresTests.__dict__
        if name.startswith("test_")
    )
