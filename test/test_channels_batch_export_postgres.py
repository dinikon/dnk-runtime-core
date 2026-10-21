"""Ручной и ежедневный пакет через настоящий API, PostgreSQL, Files/MinIO и durable jobs."""

import copy
from datetime import UTC, datetime, timedelta
import os
import unittest
from unittest.mock import patch
from urllib.parse import urlsplit
from uuid import UUID, uuid4
from defusedxml.ElementTree import fromstring
from sqlalchemy import select, update, func, insert, delete
from src.config import dnk_config
from src.modules.tenancy.infrastructure.persistence.tenant_domain import (
    TenantDomainModel as D,
)
from src.modules.channels.application.plugin_contract import HttpResultDTO
from src.modules.channels.application.port.plugin_services import PluginCallError
from src.modules.channels.infrastructure.jobs import BATCH_EXPORT_JOB, DAILY_EXPORT_JOB
from src.modules.channels.infrastructure.persistence.models.batch_export import (
    BatchExportRunModel as R,
    BatchExportItemModel as I,
)
from src.modules.channels.infrastructure.persistence.models.export_schedule import (
    ExportScheduleModel as S,
)
from src.modules.channels.infrastructure.persistence.models.product_representation import (
    ProductRepresentationModel as P,
)
from src.modules.channels.presentation.jobs.batch_export import (
    ChannelsBatchExportJobHandler,
)
from src.modules.channels.presentation.batch_export.feed_router import (
    router as feed_router,
)
from src.modules.channels.presentation.batch_export.assembly import (
    build_batch_export_handlers,
    get_export_feed_links,
)
from src.modules.channels.application.export_schedule.command.execute_daily_export.command import (
    ExecuteDailyExportCommand,
)
from src.modules.shared.infrastructure.jobs.sqlalchemy_scheduled_job_repository import (
    SqlAlchemyScheduledJobRepository,
)
from src.modules.shared.domain.jobs.scheduled_job import ScheduledJob
from test import test_channels_postgres as core
from test import test_channels_bindings_postgres as bindings
from test import test_channels_import_postgres as imports
from test import test_channels_content_update_postgres as content


class BatchTransport(core.StoreFixtureTransport):
    """Изолированная площадка читает настоящий подписанный XML из приватного MinIO."""

    def __init__(self) -> None:
        """Готовит опубликованные карточки с галереей, скидкой и отдельными ключами."""
        super().__init__()
        self.products = {
            identifier: {
                "id": identifier,
                "external_id": f"import-{identifier}",
                "sku": f"SKU-{identifier}",
                "name": f"Old {identifier}",
                "name_multilang": {"ru": "Old RU", "uk": "Old UK"},
                "description": "<p>Old RU</p>",
                "description_multilang": {"ru": "<p>Old RU</p>", "uk": "<p>Old UK</p>"},
                "price": "99.99",
                "currency": "UAH",
                "discount": {"type": "percent", "value": 10},
                "presence": "available",
                "status": "on_display",
                "quantity_in_stock": 5,
                "category": {"id": 1333, "caption": "Category"},
                "group": {"id": 900},
                "main_image": "https://img.example/1.jpg",
                "images": [
                    {"id": 1, "url": "https://img.example/1.jpg"},
                    {"id": 2, "url": "https://img.example/2.jpg"},
                ],
            }
            for identifier in (100, 101, 102)
        }
        self.client = None
        self.posts = []
        self.xml = b""
        self.lose_response = False
        self.reject = False
        self.break_price = False
        self.pending = False
        self.many = False

    async def get(
        self,
        path: str,
        *,
        query: dict[str, str] | None = None,
        headers: dict[str, str] | None = None,
    ) -> HttpResultDTO:
        """Сохраняет wire-пагинацию Prom и позволяет смоделировать задержку обработки."""
        query = query or {}
        if path.startswith("/api/v1/products/import/status/"):
            return HttpResultDTO(
                {
                    "status": "SUCCESS",
                    "total": 0 if self.pending else len(self.posts[-1]["ids"]),
                },
                {},
            )
        if path == "/api/v1/products/list" and query.get("limit") != "1":
            if "group_id" in query:
                result = await super().get(path, query=query, headers=headers)
                ids = [row["id"] for row in result.body["products"]]
                if self.many and query["group_id"] == "900":
                    ids = [
                        i
                        for i in sorted(self.products, reverse=True)
                        if "last_id" not in query or i <= int(query["last_id"])
                    ][:100]
            else:
                ids = [
                    i
                    for i in sorted(self.products, reverse=True)
                    if "last_id" not in query or i <= int(query["last_id"])
                ][:100]
            return HttpResultDTO(
                {"products": [copy.deepcopy(self.products[i]) for i in ids]}, {}
            )
        if path.startswith("/api/v1/products/") and path.rsplit("/", 1)[-1].isdecimal():
            row = self.products.get(int(path.rsplit("/", 1)[-1]))
            if row is None:
                raise PluginCallError("publication_not_found")
            return HttpResultDTO({"product": copy.deepcopy(row)}, {})
        return await super().get(path, query=query, headers=headers)

    async def post(
        self,
        path: str,
        *,
        payload: dict[str, object],
        headers: dict[str, str] | None = None,
    ) -> HttpResultDTO:
        """Подтверждает точный контракт, затем меняет только четыре текста исходных карточек."""
        if self.reject:
            raise PluginCallError("provider_request_rejected")
        assert path == "/api/v1/products/import_url"
        assert payload["updated_fields"] == [
            "name",
            "description",
            "name_ua",
            "description_ua",
        ]
        assert (
            payload["mark_missing_product_as"] == "none"
            and payload["only_available"] is False
            and payload["force_update"] is True
        )
        url = urlsplit(payload["url"])
        response = await self.client.get(url.path + "?" + url.query)
        assert response.status_code == 200, response.text
        self.xml = response.content
        ids = []
        for offer in fromstring(self.xml).findall("./shop/offers/offer"):
            matches = [
                v
                for v in self.products.values()
                if v["external_id"] == offer.attrib["id"]
            ]
            assert len(matches) == 1, "Unknown or duplicate identity reached submission"
            row = matches[0]
            ids.append(row["id"])
            assert set(child.tag for child in offer) == {
                "name",
                "description",
                "name_ua",
                "description_ua",
                "portal_category_id",
            }
            assert offer.findtext("portal_category_id") == str(row["category"]["id"])
            row["name"] = offer.findtext("name")
            row["description"] = offer.findtext("description")
            row["name_multilang"] = {"ru": row["name"], "uk": offer.findtext("name_ua")}
            row["description_multilang"] = {
                "ru": row["description"],
                "uk": offer.findtext("description_ua"),
            }
            if self.break_price:
                row["price"] = "777"
        self.posts.append({"ids": ids, "payload": copy.deepcopy(payload)})
        if self.lose_response:
            raise PluginCallError("network_error")
        return HttpResultDTO({"status": "success", "id": "test-import-1"}, {})


@unittest.skipUnless(
    os.environ.get("TEST_POSTGRES_URL") and os.environ.get("TEST_MINIO_ENDPOINT"),
    "Requires disposable PostgreSQL and MinIO",
)
class ChannelsBatchExportPostgresTests(unittest.IsolatedAsyncioTestCase):
    """Проверяет рабочую сборку с реальными транзакциями и файлами без внешнего магазина."""

    session = core.ChannelsPostgresTests.session
    request = core.ChannelsPostgresTests.request
    create = core.ChannelsPostgresTests.create
    claim = core.ChannelsPostgresTests.claim
    drain = core.ChannelsPostgresTests.drain
    catalog = bindings.ChannelsBindingsPostgresTests.catalog
    setup_bound = content.ChannelsContentUpdatePostgresTests.setup_bound

    async def asyncSetUp(self) -> None:
        """Создаёт одноразовые tenant и owned MinIO; production URLs остаются недоступны."""
        await imports.ChannelsImportPostgresTests.asyncSetUp(self)
        async with self.engine.begin() as connection:
            for tenant, host in (
                (self.tenant, "tenant.example"),
                (self.other, "other.example"),
            ):
                await connection.execute(
                    insert(D).values(
                        id=uuid4(),
                        tenant_id=tenant,
                        host=host,
                        service_type="console",
                        kind="custom",
                        status="active",
                        is_primary=True,
                    )
                )
        self.app.state.db = self.sessions
        self.app.include_router(feed_router)
        self.transport = BatchTransport()
        self.transport.client = self.client
        self.verify_worker.transport_factory = lambda _: self.transport
        self.page_worker.transport_factory = lambda _: self.transport
        self.worker = ChannelsBatchExportJobHandler(
            self.sessions,
            transport_factory=lambda _: self.transport,
            encryption_key=self.key,
            storage=self.resolver,
        )
        self.feed_patch = patch(
            "src.modules.channels.presentation.batch_export.http.controller.get_export_feed.get_storage_resolver",
            return_value=self.resolver,
        )
        self.feed_patch.start()
        self.addCleanup(self.feed_patch.stop)

    async def asyncTearDown(self) -> None:
        """Удаляет домены только собственных одноразовых tenant до общей очистки."""
        async with self.engine.begin() as connection:
            await connection.execute(
                delete(D).where(D.tenant_id.in_((self.tenant, self.other)))
            )
        await imports.ChannelsImportPostgresTests.asyncTearDown(self)

    async def deliver(self, job: ScheduledJob) -> None:
        """Использует production worker с настоящим lease; не запускает будущие дни."""
        if job.job_type not in (BATCH_EXPORT_JOB, DAILY_EXPORT_JOB):
            await core.ChannelsPostgresTests.deliver(self, job)
            return
        await self.worker.handle(job)
        async with self.sessions() as session:
            await SqlAlchemyScheduledJobRepository(session).mark_done(
                job_id=job.id, lock_token=job.lock_token, completed_at=datetime.now(UTC)
            )
            await session.commit()

    async def enabled(self, *, count: int = 1) -> tuple[dict, list[dict]]:
        """Явно разрешает Channel и выбранные связи через HTTP."""
        channel, pubs, _ = await self.setup_bound("prom", count)
        current = await self.request("GET", "/" + channel["channel_id"])
        await self.request(
            "PATCH",
            "/" + channel["channel_id"],
            {"revision": current["revision"], "is_enabled": True},
        )
        connection = current["connection_id"]
        page = await self.request("GET", f"/connections/{connection}/publications")
        selected = [
            v
            for v in page["items"]
            if v["publication_id"] in {p["publication_id"] for p in pubs}
        ]
        await self.request(
            "PATCH",
            f"/{channel['channel_id']}/publication-export",
            {
                "enabled": True,
                "items": [
                    {
                        "representation_id": v["representation_id"],
                        "expected_revision": v["representation_revision"],
                    }
                    for v in selected
                ],
            },
        )
        return channel, selected

    async def start(self, channel: dict, identifier: str | None = None) -> str:
        """Принимает идемпотентный ручной пакет."""
        result = await self.request(
            "POST",
            f"/{channel['channel_id']}/batch-exports",
            {"run_id": identifier or str(uuid4())},
            202,
        )
        return result["run_id"]

    async def detail(self, identifier: str) -> dict:
        """Читает безопасную проекцию завершённого или текущего пакета."""
        return await self.request("GET", "/batch-exports/" + identifier)

    async def test_local_file_has_tenant_url_without_post_and_releases_slot(
        self,
    ) -> None:
        """localhost отдаёт готовый XML; file-режим не записывает в Prom и не держит слот."""
        channel, _ = await self.enabled(count=2)
        before = copy.deepcopy(self.transport.products)
        async with self.engine.begin() as connection:
            await connection.execute(
                update(D).where(D.tenant_id == self.tenant).values(host="localhost")
            )
        overview = await self.request("GET", f"/{channel['channel_id']}/batch-export")
        self.assertTrue(overview["feed_available"])
        self.assertFalse(overview["delivery_configured"])
        denied = await self.request(
            "POST",
            f"/{channel['channel_id']}/batch-exports",
            {"run_id": str(uuid4())},
            503,
        )
        self.assertEqual(denied["detail"], "batch_export_requires_public_host")
        identifier = str(uuid4())
        await self.request(
            "POST",
            f"/{channel['channel_id']}/batch-exports",
            {"run_id": identifier, "delivery_mode": "file"},
            202,
        )
        preparing = await self.detail(identifier)
        self.assertIsNone(preparing["feed_url"])
        await self.drain()
        result = await self.detail(identifier)
        self.assertEqual(result["run"]["status"], "prepared", result)
        self.assertEqual(result["run"]["delivery_mode"], "file")
        self.assertFalse(result["run"]["interrupted"])
        self.assertTrue(
            result["feed_url"].startswith(
                "http://localhost/api/channels/batch-exports/"
            )
        )
        response = await self.client.get(result["feed_url"])
        self.assertEqual(response.status_code, 200, response.text)
        self.assertIn("application/xml", response.headers["content-type"])
        self.assertIn("inline", response.headers["content-disposition"])
        offers = fromstring(response.content).findall("shop/offers/offer")
        self.assertEqual(len(offers), 2)
        for offer in offers:
            self.assertEqual(
                {e.tag for e in offer},
                {
                    "name",
                    "description",
                    "name_ua",
                    "description_ua",
                    "portal_category_id",
                },
            )
            self.assertTrue(
                all(
                    offer.findtext(key)
                    for key in ("name", "description", "name_ua", "description_ua")
                )
            )
        self.assertEqual(self.transport.posts, [])
        self.assertEqual(before, self.transport.products)
        await self.request(
            "POST",
            f"/{channel['channel_id']}/batch-exports",
            {"run_id": identifier, "delivery_mode": "provider"},
            409,
        )
        second = str(uuid4())
        new = await self.request(
            "POST",
            f"/{channel['channel_id']}/batch-exports",
            {"run_id": second, "delivery_mode": "file"},
            202,
        )
        self.assertEqual(new["run_id"], second)

    async def test_registered_domain_change_and_api_fallback_need_no_global_url(
        self,
    ) -> None:
        """Фасад предпочитает Console, затем активный API; смена домена сразу меняет URL."""
        from src.modules.channels.infrastructure.batch_export.tenant_feed_links import (
            TenantExportFeedLinks,
        )
        from src.modules.tenancy.infrastructure.tenant_domain.public_hosts import (
            SqlAlchemyTenantPublicHosts,
        )

        run_id = uuid4()
        expires = datetime.now(UTC) + timedelta(hours=1)
        async with self.engine.begin() as connection:
            await connection.execute(
                insert(D).values(
                    id=uuid4(),
                    tenant_id=self.tenant,
                    host="api.tenant.example",
                    service_type="http",
                    kind="custom",
                    status="active",
                    is_primary=True,
                )
            )
        async with self.session() as session:
            links = TenantExportFeedLinks(
                SqlAlchemyTenantPublicHosts(session), get_export_feed_links()
            )
            self.assertTrue(
                (await links.url(self.tenant, run_id, expires)).startswith(
                    "https://tenant.example/"
                )
            )
            await session.execute(
                update(D)
                .where(D.tenant_id == self.tenant, D.service_type == "console")
                .values(status="disabled")
            )
            self.assertTrue(
                (await links.url(self.tenant, run_id, expires)).startswith(
                    "https://api.tenant.example/"
                )
            )
            await session.execute(
                update(D)
                .where(D.tenant_id == self.tenant, D.service_type == "http")
                .values(host="new.tenant.example")
            )
            self.assertTrue(
                (await links.url(self.tenant, run_id, expires)).startswith(
                    "https://new.tenant.example/"
                )
            )
            self.assertTrue((await links.availability(self.tenant)).delivery_configured)

    async def test_feed_rejects_foreign_host_and_expired_artifact(self) -> None:
        """Подпись не обходит принадлежность host, а просроченная ссылка не показывается."""
        channel, _ = await self.enabled()
        identifier = await self.start(channel)
        await self.drain()
        result = await self.detail(identifier)
        self.assertTrue(result["feed_url"].startswith("https://tenant.example/"))
        self.assertEqual((await self.client.get(result["feed_url"])).status_code, 200)
        for host in ("other.example", "unknown.example"):
            response = await self.client.get(result["feed_url"], headers={"Host": host})
            self.assertEqual(response.status_code, 404)
        async with self.engine.begin() as connection:
            await connection.execute(
                update(D).where(D.tenant_id == self.tenant).values(status="disabled")
            )
        self.assertEqual((await self.client.get(result["feed_url"])).status_code, 404)
        async with self.engine.begin() as connection:
            await connection.execute(
                update(D).where(D.tenant_id == self.tenant).values(status="active")
            )
        async with self.session() as session:
            await session.execute(
                update(R)
                .where(R.id == UUID(identifier))
                .values(
                    created_at=datetime.now(UTC) - timedelta(days=8),
                    expires_at=datetime.now(UTC) - timedelta(seconds=1),
                )
            )
        self.assertIsNone((await self.detail(identifier))["feed_url"])
        self.assertEqual((await self.client.get(result["feed_url"])).status_code, 404)

    async def test_manual_full_pipeline_file_and_preserved_fields(self) -> None:
        """API → Jobs → Catalog snapshots → Files → XML → Prom fixture → readback."""
        channel, pubs = await self.enabled(count=2)
        before = copy.deepcopy(self.transport.products)
        identifier = await self.start(channel)
        duplicate = await self.start(channel, str(uuid4()))
        self.assertEqual(identifier, duplicate)
        await self.drain()
        result = await self.detail(identifier)
        self.assertEqual(result["run"]["status"], "succeeded", result)
        self.assertEqual(result["run"]["counts"], {"verified": 2})
        self.assertEqual(len(self.transport.posts), 1)
        self.assertIn(
            b"<portal_category_id>1333</portal_category_id>", self.transport.xml
        )
        self.assertEqual(set(before), set(self.transport.products))
        allowed = {"name", "description", "name_multilang", "description_multilang"}
        for native, row in self.transport.products.items():
            self.assertEqual(
                {k: v for k, v in row.items() if k not in allowed},
                {k: v for k, v in before[native].items() if k not in allowed},
            )
        self.assertNotIn("provider_context", str(result))
        self.assertNotIn("private-token", str(result))
        # A signed file cannot be moved to another operation or fetched without capability.
        link = self.transport.posts[0]["payload"]["url"]
        parsed = urlsplit(link)
        self.assertEqual((await self.client.get(parsed.path)).status_code, 422)
        self.assertEqual(
            (await self.client.get(parsed.path + "?access=invalid")).status_code, 422
        )
        self.assertEqual(
            (
                await self.client.get(
                    parsed.path.replace(identifier, str(uuid4())) + "?" + parsed.query
                )
            ).status_code,
            404,
        )

    async def test_flags_default_off_and_no_implicit_enabling(self) -> None:
        """Активная связь не попадает в пакет до явного разрешения экспорта."""
        channel, pubs, _ = await self.setup_bound("prom")
        current = await self.request("GET", "/" + channel["channel_id"])
        await self.request(
            "PATCH",
            "/" + channel["channel_id"],
            {"revision": current["revision"], "is_enabled": True},
        )
        identifier = await self.start(channel)
        await self.drain()
        self.assertEqual((await self.detail(identifier))["run"]["status"], "empty")
        self.assertEqual(self.transport.posts, [])
        overview = await self.request("GET", f"/{channel['channel_id']}/batch-export")
        self.assertEqual(overview["enabled_count"], 0)
        self.assertFalse(overview["schedule"]["enabled"])

    async def test_missing_duplicate_hidden_and_missing_content_are_skipped(
        self,
    ) -> None:
        """Конфликтные ключи и скрытые карточки исключаются до передачи файла."""
        channel, pubs = await self.enabled(count=3)
        native = [int(p["external_id"]) for p in pubs]
        self.transport.products[native[0]]["external_id"] = None
        self.transport.products[native[1]]["status"] = "not_on_display"
        self.transport.products[999] = copy.deepcopy(self.transport.products[native[2]])
        self.transport.products[999]["id"] = 999
        identifier = await self.start(channel)
        await self.drain()
        result = await self.detail(identifier)
        self.assertEqual(result["run"]["status"], "empty", result)
        self.assertEqual(result["run"]["counts"], {"skipped": 3})
        self.assertEqual(self.transport.posts, [])

    async def test_ambiguous_post_never_repeats_on_resume(self) -> None:
        """Потерянный ответ держит слот; повтор проверки не выполняет второй POST."""
        channel, _ = await self.enabled()
        self.transport.lose_response = True
        identifier = await self.start(channel)
        await self.drain()
        self.assertEqual((await self.detail(identifier))["run"]["status"], "unknown")
        await self.request("POST", "/batch-exports/" + identifier + "/resume", {}, 202)
        await self.drain()
        self.assertEqual(len(self.transport.posts), 1)
        self.assertEqual((await self.detail(identifier))["run"]["status"], "unknown")
        self.assertEqual(await self.start(channel), identifier)

    async def test_non_text_field_change_is_reported(self) -> None:
        """Даже подтверждённые тексты не означают успех при изменении цены площадкой."""
        channel, _ = await self.enabled()
        self.transport.break_price = True
        identifier = await self.start(channel)
        await self.drain()
        result = await self.detail(identifier)
        self.assertEqual(result["run"]["status"], "failed")
        self.assertIn("export_preserved_fields_changed", result["items"][0]["issues"])

    async def test_binding_permission_changed_before_send_blocks_whole_snapshot(
        self,
    ) -> None:
        """Снятие разрешения во время подготовки запрещает передачу устаревшего состава."""
        channel, pubs = await self.enabled()
        identifier = await self.start(channel)
        for _ in range(15):
            result = await self.detail(identifier)
            if result["run"]["status"] == "ready":
                self.assertIsNone(result["feed_url"])
                break
            for job in await self.claim():
                await self.deliver(job)
        async with self.session() as session:
            await session.execute(
                update(P)
                .where(P.id == UUID(pubs[0]["representation_id"]))
                .values(export_enabled=False)
            )
        await self.drain()
        self.assertEqual((await self.detail(identifier))["run"]["status"], "failed")
        self.assertIsNone((await self.detail(identifier))["feed_url"])
        self.assertEqual(self.transport.posts, [])

    async def test_daily_is_durable_idempotent_and_manual_does_not_move_it(
        self,
    ) -> None:
        """Сохранённая policy переживает worker recreation; повтор события — no-op."""
        channel, _ = await self.enabled()
        channel_id = UUID(channel["channel_id"])
        overview = await self.request("GET", f"/{channel_id}/batch-export")
        schedule = await self.request(
            "PUT",
            f"/{channel_id}/export-schedule",
            {
                "enabled": True,
                "hour": 3,
                "minute": 0,
                "timezone": "Europe/Kyiv",
                "expected_revision": overview["schedule"]["revision"],
            },
        )
        manual = await self.start(channel)
        await self.drain()
        next_after = (await self.request("GET", f"/{channel_id}/batch-export"))[
            "schedule"
        ]["next_at"]
        self.assertEqual(schedule["next_at"], next_after)
        now = datetime.now(UTC) - timedelta(seconds=1)
        async with self.session() as session:
            await session.execute(
                update(S).where(S.channel_id == channel_id).values(next_at=now)
            )
        command = ExecuteDailyExportCommand(
            self.tenant, channel_id, schedule["revision"], now
        )
        async with self.session() as session:
            await build_batch_export_handlers(
                session, self.worker.registry
            ).access.jobs.daily_export(
                self.tenant, channel_id, schedule["revision"], now
            )
        # Реальное due-событие проходит через production job handler и его lease.
        await self.drain()
        async with self.session() as session:
            await build_batch_export_handlers(
                session, self.worker.registry
            ).daily.execute(command)
        await self.drain()
        recent = (await self.request("GET", f"/{channel_id}/batch-export"))["recent"]
        self.assertEqual(len(recent), 2)
        self.assertEqual(sorted(v["trigger"] for v in recent), ["daily", "manual"])
        self.assertTrue(all(v["status"] == "succeeded" for v in recent), recent)

    async def test_tenant_and_csrf_boundaries_and_export_filter(self) -> None:
        """Фильтр соответствует флагам; чужая схема и запрос без CSRF не принимаются."""
        channel, pubs = await self.enabled()
        current = await self.request("GET", "/" + channel["channel_id"])
        page = await self.request(
            "GET",
            f"/connections/{current['connection_id']}/publications?export_status=enabled",
        )
        self.assertEqual(page["total"], 1)
        self.assertTrue(page["items"][0]["export_enabled"])
        denied = await self.client.post(
            f"/api/console/channels/{channel['channel_id']}/batch-exports",
            json={"run_id": str(uuid4())},
        )
        self.assertEqual(denied.status_code, 403)
        identifier = await self.start(channel)
        # Swap only the trusted principal, as existing tenant integration tests do.
        from src.modules.identity.domain.auth.principal import Principal
        from src.modules.identity.domain.auth.request_context import RequestContext
        from test.crm_company_support import company_app
        from src.modules.channels.presentation.router import router
        from httpx import AsyncClient, ASGITransport

        app = company_app(
            self.sessions,
            RequestContext(
                Principal(str(self.actor), str(self.other), "test", ("member",)),
                None,
                None,
                None,
            ),
            scoped_connection=True,
        )
        app.include_router(router, prefix="/api/console")
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="https://other.example"
        ) as client:
            response = await client.get(
                "/api/console/channels/batch-exports/" + identifier
            )
            self.assertEqual(response.status_code, 404)

    async def test_concurrent_start_and_lost_job_resume(self) -> None:
        """Одновременные намерения используют один слот; потерянный job виден и восстанавливается."""
        import asyncio
        from src.modules.shared.infrastructure.jobs.scheduled_job_model import (
            ScheduledJobModel,
        )

        channel, _ = await self.enabled()
        identifiers = await asyncio.gather(*[self.start(channel) for _ in range(6)])
        self.assertEqual(len(set(identifiers)), 1)
        identifier = identifiers[0]
        async with self.sessions() as session:
            await session.execute(
                update(ScheduledJobModel)
                .where(
                    ScheduledJobModel.tenant_id == self.tenant,
                    ScheduledJobModel.job_type == BATCH_EXPORT_JOB,
                )
                .values(status="failed")
            )
            await session.commit()
        self.assertTrue((await self.detail(identifier))["run"]["interrupted"])
        await self.request("POST", f"/batch-exports/{identifier}/resume", {}, 202)
        await self.drain()
        self.assertEqual((await self.detail(identifier))["run"]["status"], "succeeded")
        self.assertEqual(len(self.transport.posts), 1)

    async def test_preflight_skip_keeps_other_targets_in_same_file(self) -> None:
        """Неподдерживаемая карточка пропускается, остальные получают один общий импорт."""
        channel, pubs = await self.enabled(count=3)
        self.transport.products[int(pubs[0]["external_id"])][
            "status"
        ] = "not_on_display"
        identifier = await self.start(channel)
        await self.drain()
        result = await self.detail(identifier)
        self.assertEqual(result["run"]["status"], "partial")
        self.assertEqual(result["run"]["counts"], {"skipped": 1, "verified": 2})
        self.assertEqual(len(self.transport.posts), 1)
        self.assertEqual(len(self.transport.posts[0]["ids"]), 2)

    async def test_worker_recovery_after_claim_does_not_submit(self) -> None:
        """Crash после фиксации submitting оставляет неопределённость, не повторяет запись."""
        from src.modules.channels.application.batch_export.command.prepare_batch_export_step.command import (
            PrepareBatchExportStepCommand,
        )
        from src.modules.shared.infrastructure.jobs.scheduled_job_model import (
            ScheduledJobModel,
        )

        channel, _ = await self.enabled()
        identifier = await self.start(channel)
        for _ in range(20):
            result = await self.detail(identifier)
            if result["run"]["status"] == "ready":
                break
            for job in await self.claim():
                await self.deliver(job)
        async with self.session() as session:
            run = await build_batch_export_handlers(
                session, self.worker.registry
            ).access.runs.get(UUID(identifier))
            prepared = await build_batch_export_handlers(
                session, self.worker.registry
            ).prepare.execute(
                PrepareBatchExportStepCommand(self.tenant, run.id, run.sequence)
            )
        self.assertEqual(prepared.mode, "submit")
        async with self.sessions() as session:
            await session.execute(
                update(ScheduledJobModel)
                .where(
                    ScheduledJobModel.tenant_id == self.tenant,
                    ScheduledJobModel.job_type == BATCH_EXPORT_JOB,
                )
                .values(run_at=datetime.now(UTC) - timedelta(seconds=1))
            )
            await session.commit()
        await self.drain()
        self.assertEqual((await self.detail(identifier))["run"]["status"], "unknown")
        self.assertEqual(self.transport.posts, [])

    async def test_batch_larger_than_fifty_is_one_file_without_truncation(self) -> None:
        """Общее ядро не наследует лимит 50 позиций ручного Woo preview."""
        self.transport.many = True
        for identifier in range(200, 248):
            row = copy.deepcopy(self.transport.products[102])
            row["id"] = identifier
            row["external_id"] = f"import-{identifier}"
            self.transport.products[identifier] = row
        channel, connection = await self.create("prom")
        await self.drain()
        page = await self.request(
            "GET", f"/connections/{connection['connection_id']}/publications?limit=100"
        )
        self.assertEqual(page["total"], 51)
        for index, pub in enumerate(page["items"]):
            item = await self.catalog(
                "POST",
                body={
                    "translations": {
                        locale: {
                            "expected_schema_version": 1,
                            "values": {
                                "title": f"{locale} {index}",
                                "body": f"<p>Body {locale} {index}</p>",
                            },
                        }
                        for locale in ("ru", "uk")
                    }
                },
                status=201,
            )
            await self.request(
                "POST",
                f"/publications/{pub['publication_id']}/binding",
                {"catalog_item_id": item["id"]},
                201,
            )
        page = await self.request(
            "GET", f"/connections/{connection['connection_id']}/publications?limit=100"
        )
        await self.request(
            "PATCH",
            f"/{channel['channel_id']}/publication-export",
            {
                "enabled": True,
                "items": [
                    {
                        "representation_id": v["representation_id"],
                        "expected_revision": v["representation_revision"],
                    }
                    for v in page["items"]
                ],
            },
        )
        current = await self.request("GET", "/" + channel["channel_id"])
        await self.request(
            "PATCH",
            "/" + channel["channel_id"],
            {"revision": current["revision"], "is_enabled": True},
        )
        identifier = await self.start(channel)
        for _ in range(200):
            jobs = await self.claim()
            if not jobs:
                break
            for job in jobs:
                await self.deliver(job)
        result = await self.detail(identifier)
        self.assertEqual(result["run"]["status"], "succeeded", result["run"])
        self.assertEqual(result["total"], 51)
        self.assertEqual(result["run"]["counts"], {"verified": 51})
        self.assertEqual(len(self.transport.posts), 1)
        self.assertEqual(
            len(fromstring(self.transport.xml).findall("./shop/offers/offer")), 51
        )

    async def test_disabling_outbound_after_acceptance_still_verifies_and_does_not_resend(
        self,
    ) -> None:
        """Отключение Channel останавливает новые записи, но не теряет результат принятого импорта."""
        channel, _ = await self.enabled()
        identifier = await self.start(channel)
        for _ in range(20):
            result = await self.detail(identifier)
            if result["run"]["status"] == "processing":
                break
            for job in await self.claim():
                await self.deliver(job)
        self.assertEqual(len(self.transport.posts), 1)
        current = await self.request("GET", "/" + channel["channel_id"])
        await self.request(
            "PATCH",
            "/" + channel["channel_id"],
            {"revision": current["revision"], "is_enabled": False},
        )
        await self.drain()
        self.assertEqual((await self.detail(identifier))["run"]["status"], "succeeded")
        self.assertEqual(len(self.transport.posts), 1)
        await self.request(
            "POST",
            f"/{channel['channel_id']}/batch-exports",
            {"run_id": str(uuid4())},
            503,
        )

    async def test_signed_feed_closes_stream_before_response_body_on_error(
        self,
    ) -> None:
        """Request cleanup освобождает MinIO даже при ошибке до первого байта XML."""
        channel, _ = await self.enabled()
        identifier = await self.start(channel)
        await self.drain()
        url = urlsplit(self.transport.posts[0]["payload"]["url"])
        closed = []
        original_open = self.adapter.open

        from src.modules.files.application.port.storage import (
            StorageLocation,
            FileContentStream,
        )
        from collections.abc import AsyncIterator

        async def tracking_open(
            location: StorageLocation, key: str
        ) -> FileContentStream:
            """Оборачивает реальный поток для проверки публичного close-контракта."""
            source = await original_open(location, key)

            class Stream:
                """Передаёт чтение и фиксирует освобождение ресурса."""

                def __aiter__(self) -> AsyncIterator[bytes]:
                    """Возвращает источник XML."""
                    return self

                async def __anext__(self) -> bytes:
                    """Читает порцию настоящего объекта."""
                    return await source.__anext__()

                async def aclose(self) -> None:
                    """Освобождает MinIO независимо от запуска итератора ответа."""
                    closed.append(True)
                    await source.aclose()

            return Stream()

        with (
            patch.object(self.adapter, "open", side_effect=tracking_open),
            patch(
                "src.modules.channels.presentation.batch_export.http.controller.get_export_feed.ExportFeedResponse",
                side_effect=ValueError("response_fixture_failure"),
            ),
        ):
            with self.assertRaises(ValueError):
                await self.client.get(url.path + "?" + url.query)
        self.assertTrue(closed)

    async def test_daily_preserves_next_day_when_public_delivery_temporarily_unconfigured(
        self,
    ) -> None:
        """Недоступная deployment-настройка пропускает день, сохраняя следующее durable событие."""
        channel, _ = await self.enabled()
        channel_id = UUID(channel["channel_id"])
        await self.request(
            "PUT",
            f"/{channel_id}/export-schedule",
            {
                "enabled": True,
                "hour": 3,
                "minute": 0,
                "timezone": "Europe/Kyiv",
                "expected_revision": 1,
            },
        )
        now = datetime.now(UTC) - timedelta(seconds=1)
        async with self.session() as session:
            await session.execute(
                update(S).where(S.channel_id == channel_id).values(next_at=now)
            )
            await build_batch_export_handlers(
                session, self.worker.registry
            ).access.jobs.daily_export(self.tenant, channel_id, 2, now)
        async with self.engine.begin() as connection:
            await connection.execute(
                update(D).where(D.tenant_id == self.tenant).values(host="localhost")
            )
        await self.drain()
        overview = await self.request("GET", f"/{channel_id}/batch-export")
        self.assertFalse(overview["delivery_configured"])
        self.assertTrue(overview["schedule"]["enabled"])
        self.assertGreater(
            datetime.fromisoformat(overview["schedule"]["next_at"]), datetime.now(UTC)
        )
        self.assertEqual(overview["recent"], [])
        self.assertEqual(self.transport.posts, [])
