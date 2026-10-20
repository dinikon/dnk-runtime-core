"""HTTP → durable queue → read plugins → PostgreSQL без внешних записей."""

import asyncio
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
import os
import unittest
from unittest.mock import AsyncMock, patch
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo
from cryptography.fernet import Fernet
from httpx import AsyncClient, ASGITransport
from sqlalchemy import text, select, insert, delete, update, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool
from sqlalchemy.schema import CreateSchema, DropSchema
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from src.config import dnk_config
from src.config.feature.channels_config import ChannelsSettings
from src.modules.channels.presentation.router import router
from src.modules.channels.presentation.jobs.verification import (
    ChannelsVerificationJobHandler,
)
from src.modules.channels.presentation.jobs.initialization import (
    ChannelsInitializationJobHandler,
)
from src.modules.channels.infrastructure.jobs import VERIFY_JOB, PAGE_JOB
from src.modules.channels.infrastructure.persistence.models.channel import ChannelModel
from src.modules.channels.infrastructure.persistence.models.connection import (
    ConnectionModel,
)
from src.modules.channels.infrastructure.persistence.models.sync_run import SyncRunModel
from src.modules.channels.infrastructure.persistence.models.external_publication import (
    ExternalPublicationModel,
)
from src.modules.channels.application.plugin_contract import HttpResultDTO
from src.modules.channels.application.port.plugin_services import PluginCallError
from src.modules.identity.domain.auth.principal import Principal
from src.modules.identity.domain.auth.request_context import RequestContext
from src.modules.identity.presentation.access.depends import get_authorization_service
from src.modules.shared.infrastructure.persistence.global_migrations import (
    GlobalMigrator,
)
from src.modules.shared.infrastructure.persistence.unit_of_work.sqlalchemy import (
    UnitOfWork,
)
from src.modules.shared.infrastructure.jobs.sqlalchemy_scheduled_job_repository import (
    SqlAlchemyScheduledJobRepository,
)
from src.modules.shared.infrastructure.jobs.scheduled_job_model import ScheduledJobModel
from src.modules.shared.application.jobs.scheduled_job_deferred import (
    ScheduledJobDeferred,
)
from src.modules.shared.domain.jobs.scheduled_job import ScheduledJob
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_migrations import (
    TenantMigrator,
)
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_migration_metadata import (
    migration_metadata,
)
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_connection import (
    bind_tenant_schema,
)
from src.modules.tenancy.infrastructure.persistence.tenant import TenantModel
from src.modules.tenancy.application.tenant.tenant_schema_naming import (
    TenantSchemaNaming,
)
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from test.crm_company_support import company_app

URL = os.environ.get("TEST_POSTGRES_URL")


class StoreFixtureTransport:
    """Официальные wire shapes Prom/Woo с несколькими страницами и variation потоком."""

    def __init__(self) -> None:
        """Готовит изменяемые условия отказов и callback для конкурентных проверок."""
        self.calls: list[tuple[str, dict[str, str]]] = []
        self.denied = False
        self.empty = False
        self.fail_page = False
        self.callback: Callable[[], Awaitable[None]] | None = None
        self.price = "123.450000000001"
        self.prom_discount = {"value": 10, "type": "percent"}

    async def get(
        self,
        path: str,
        *,
        query: dict[str, str] | None = None,
        headers: dict[str, str] | None = None,
    ) -> HttpResultDTO:
        """Возвращает только fixture JSON; не открывает реальное сетевое соединение."""
        query = query or {}
        self.calls.append((path, dict(query)))
        if path == "/wp-json/":
            if headers and "Authorization" in headers:
                raise AssertionError("WooCommerce credentials leaked to WordPress root")
            return HttpResultDTO({"url": "https://shop.example"}, {})
        if not headers or "Authorization" not in headers:
            raise AssertionError("Credentials facade was not used")
        if self.callback:
            callback, self.callback = (self.callback, None)
            await callback()
        if self.denied:
            raise PluginCallError("permission_denied")
        if path == "/wp-json/wc/v3/products":
            if self.fail_page and query.get("page") == "2":
                raise PluginCallError("provider_request_rejected")
            if self.empty:
                return HttpResultDTO([], {})
            page = int(query.get("page", "1"))
            rows = {
                1: [
                    {
                        "id": 10,
                        "name": "<b>Товар</b>",
                        "sku": "SAME",
                        "type": "simple",
                        "regular_price": self.price,
                        "sale_price": "100",
                        "stock_quantity": 0,
                        "stock_status": "outofstock",
                        "images": [{"src": "https://img.example/main.jpg"}],
                        "description": "<script>bad()</script><p>Description</p>",
                        "meta_data": [{"key": "token", "value": "DO_NOT_COPY"}],
                    },
                    {
                        "id": 20,
                        "name": "Variable",
                        "sku": "SAME",
                        "type": "variable",
                        "stock_status": "instock",
                    },
                ],
                2: [
                    {
                        "id": 30,
                        "name": "Draft product",
                        "status": "draft",
                        "type": "simple",
                        "regular_price": "0",
                        "stock_quantity": "1.25",
                        "stock_status": "instock",
                    }
                ],
            }.get(page, [])
            return HttpResultDTO(rows[:1] if query.get("per_page") == "1" else rows, {})
        if "/variations" in path:
            rows = (
                [
                    {
                        "id": 21,
                        "sku": "VAR-1",
                        "regular_price": "12.22",
                        "stock_quantity": None,
                        "stock_status": "onbackorder",
                    },
                    {
                        "id": 22,
                        "name": "Variant",
                        "regular_price": "bad",
                        "stock_status": "instock",
                    },
                ]
                if query.get("page") == "1" and (not self.empty)
                else []
            )
            return HttpResultDTO(rows, {})
        if path == "/api/v1/groups/list":
            return HttpResultDTO(
                {
                    "groups": (
                        [{"id": 900}, {"id": 800}]
                        if "last_id" not in query and (not self.empty)
                        else []
                    )
                },
                {},
            )
        if path == "/api/v1/products/list":
            if query.get("limit") == "1":
                return HttpResultDTO({"group_id": 1000, "products": []}, {})
            group = int(query["group_id"])
            ids = (
                {1000: [102], 900: [102, 101], 800: [100]}.get(group, [])
                if "last_id" not in query and (not self.empty)
                else []
            )
            return HttpResultDTO(
                {
                    "group_id": group,
                    "products": [
                        {
                            "id": identifier,
                            "external_id": f"import-{identifier}",
                            "sku": "SAME",
                            "name": f"Prom {identifier}",
                            "price": Decimal("99.99"),
                            "currency": "UAH",
                            "presence": "available",
                            "status": "on_display",
                            "group": {"id": group},
                            "main_image": "https://img.example/prom.jpg",
                            "discount": self.prom_discount,
                        }
                        for identifier in ids
                    ],
                },
                {},
            )
        raise AssertionError("Unexpected fixture route " + path)


@unittest.skipUnless(URL, "TEST_POSTGRES_URL must point to a disposable database")
class ChannelsPostgresTests(unittest.IsolatedAsyncioTestCase):
    """Проверяет настоящие транзакции, tenant isolation и доставку фоновых шагов."""

    async def asyncSetUp(self) -> None:
        """Создаёт две новые tenant-схемы, auth/CSRF и реальные worker assemblies."""
        self.engine = create_async_engine(URL, poolclass=NullPool)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        self.tenant, self.other, self.actor = (uuid4(), uuid4(), uuid4())
        self.naming = TenantSchemaNaming(dnk_config.SCHEMA_PREFIX)
        self.schemas = {
            tenant: self.naming.schema_name(EntityIdVO(tenant))
            for tenant in (self.tenant, self.other)
        }
        self.key = Fernet.generate_key().decode()
        self.config_patch = patch.object(
            dnk_config,
            "CHANNELS",
            ChannelsSettings(credentials_encryption_key=self.key),
        )
        self.config_patch.start()
        async with self.engine.begin() as connection:
            await GlobalMigrator().upgrade(connection)
            for locale in ("uk", "ru"):
                await connection.execute(
                    text(
                        "INSERT INTO public.ref_locales(code,language_code,name,active) VALUES (:code,:code,:code,true) ON CONFLICT(code) DO UPDATE SET active=true"
                    ),
                    {"code": locale},
                )
            await connection.execute(
                text(
                    "INSERT INTO public.ref_currencies(code,numeric_code,name,minor_units,active) VALUES ('UAH','980','UAH',2,true) ON CONFLICT(code) DO UPDATE SET active=true"
                )
            )
            for tenant, schema in self.schemas.items():
                await connection.execute(CreateSchema(schema))
                await TenantMigrator().upgrade(connection, schema)
                await connection.execute(
                    insert(TenantModel).values(
                        id=tenant,
                        name="Channels test",
                        external_id=str(tenant),
                        status="active",
                    )
                )
        context = RequestContext(
            Principal(str(self.actor), str(self.tenant), "test", ("member",)),
            None,
            None,
            None,
        )
        self.app = company_app(self.sessions, context, scoped_connection=True)
        self.app.include_router(router, prefix="/api/console")
        origin = (
            "http" if dnk_config.AUTH.allow_insecure_http else "https"
        ) + "://tenant.example"
        self.client = AsyncClient(
            transport=ASGITransport(app=self.app), base_url=origin
        )
        csrf = (await self.client.get("/csrf")).json()["csrf_token"]
        self.headers = {"Origin": origin, "X-CSRF-Token": csrf}
        self.transport = StoreFixtureTransport()
        self.verify_worker = ChannelsVerificationJobHandler(
            self.sessions,
            transport_factory=lambda _: self.transport,
            encryption_key=self.key,
        )
        self.page_worker = ChannelsInitializationJobHandler(
            self.sessions,
            transport_factory=lambda _: self.transport,
            encryption_key=self.key,
        )

    async def asyncTearDown(self) -> None:
        """Удаляет только собственные jobs, tenant-записи и одноразовые схемы."""
        await self.client.aclose()
        async with self.engine.begin() as connection:
            await connection.execute(
                delete(ScheduledJobModel).where(
                    ScheduledJobModel.tenant_id.in_((self.tenant, self.other))
                )
            )
            for schema in self.schemas.values():
                await connection.execute(DropSchema(schema, cascade=True))
            await connection.execute(
                delete(TenantModel).where(TenantModel.id.in_((self.tenant, self.other)))
            )
        self.config_patch.stop()
        await self.engine.dispose()

    @asynccontextmanager
    async def session(self, tenant: UUID | None = None) -> AsyncIterator[AsyncSession]:
        """Открывает внешнюю tenant-транзакцию с реальным schema_translate_map."""
        async with self.engine.connect() as connection:
            await bind_tenant_schema(connection, tenant or self.tenant, self.naming)
            async with UnitOfWork(
                async_sessionmaker(connection, expire_on_commit=False)
            ) as uow:
                yield uow.session

    async def request(
        self, method: str, path: str, body: dict | None = None, status: int = 200
    ) -> dict:
        """Выполняет реальный HTTP контракт с доверенным контекстом и CSRF."""
        response = await self.client.request(
            method, "/api/console/channels" + path, json=body, headers=self.headers
        )
        self.assertEqual(response.status_code, status, response.text)
        return response.json() if status != 204 else {}

    async def create(self, kind: str = "woocommerce") -> tuple[dict, dict]:
        """Создаёт канал и единственное подключение через production controllers."""
        channel = await self.request(
            "POST", "", {"name": "Shop", "platform_kind": kind}, 201
        )
        connection = await self.request(
            "POST",
            f"/{channel['channel_id']}/connection",
            {
                "revision": channel["revision"],
                "credentials": (
                    {"consumer_key": "key", "consumer_secret": "secret"}
                    if kind == "woocommerce"
                    else {"token": "private-token"}
                ),
                "endpoint": (
                    "https://shop.example"
                    if kind == "woocommerce"
                    else "https://my.prom.ua"
                ),
                "settings": {
                    "locales": ["uk"] if kind == "woocommerce" else ["ru", "uk"],
                    "currency": "UAH",
                },
            },
            201,
        )
        return (channel, connection)

    async def claim(self) -> list[ScheduledJob]:
        """Захватывает только собственные due jobs настоящим SQL repository."""
        async with self.sessions() as session:
            jobs = await SqlAlchemyScheduledJobRepository(session).claim_due_jobs(
                limit=100,
                now=datetime.now(UTC) + timedelta(seconds=65),
                locked_until=datetime.now(UTC) + timedelta(minutes=5),
                lock_token=str(uuid4()),
            )
            await session.commit()
            return [job for job in jobs if job.tenant_id in (self.tenant, self.other)]

    async def deliver(self, job: ScheduledJob) -> None:
        """Вызывает тот же handler, который зарегистрирован в production worker."""
        worker = self.verify_worker if job.job_type == VERIFY_JOB else self.page_worker
        await worker.handle(job)
        async with self.sessions() as session:
            await SqlAlchemyScheduledJobRepository(session).mark_done(
                job_id=job.id, lock_token=job.lock_token, completed_at=datetime.now(UTC)
            )
            await session.commit()

    async def drain(self) -> None:
        """Обрабатывает finite очередь и падает при неожиданном зацикливании."""
        for _ in range(50):
            jobs = await self.claim()
            if not jobs:
                return
            for job in jobs:
                await self.deliver(job)
        self.fail("Initialization did not terminate")

    async def test_full_woocommerce_flow_variations_and_default_off(self) -> None:
        """Загрузка проходит при sync=false, читает все страницы и не меняет Catalog."""
        channel, connection = await self.create()
        self.assertFalse(channel["is_enabled"])
        await self.drain()
        details = await self.request("GET", f"/{channel['channel_id']}/connection")
        self.assertEqual(details["verification_status"], "verified")
        self.assertNotIn("secret", str(details))
        progress = await self.request(
            "GET", f"/connections/{connection['connection_id']}/initialization"
        )
        self.assertEqual(progress["status"], "partial")
        self.assertEqual(progress["scope_limitations"], ["api_visible_statuses_only"])
        self.assertEqual(progress["processed"], 5)
        rows = await self.request(
            "GET", f"/connections/{connection['connection_id']}/publications"
        )
        self.assertEqual(rows["total"], 5)
        item = next((row for row in rows["items"] if row["external_id"] == "10"))
        self.assertEqual(Decimal(item["price"]), Decimal("123.450000000001"))
        self.assertEqual(Decimal(item["sale_price"]), Decimal("100"))
        self.assertEqual(Decimal(item["quantity"]), 0)
        self.assertEqual(item["stock_status"], "out_of_stock")
        self.assertNotIn("extensions", item)
        detail = await self.request("GET", f"/publications/{item['publication_id']}")
        self.assertNotIn("DO_NOT_COPY", str(detail))
        self.assertNotIn("<script", str(detail))
        async with self.session() as session:
            self.assertEqual(
                await session.scalar(
                    text(
                        "SELECT count(*) FROM "
                        + self.schemas[self.tenant]
                        + ".catalog_item"
                    )
                ),
                0,
            )
            self.assertFalse(await session.scalar(select(ChannelModel.is_enabled)))
        self.assertEqual(
            sum(
                (1 for path, _ in self.transport.calls if path.endswith("/variations"))
            ),
            2,
        )

    async def test_prom_groups_native_identity_and_duplicate_rows(self) -> None:
        """Обходит все группы, а повтор native ID не создаёт вторую публикацию."""
        _, connection = await self.create("prom")
        await self.drain()
        rows = await self.request(
            "GET", f"/connections/{connection['connection_id']}/publications"
        )
        self.assertEqual(rows["total"], 3)
        self.assertEqual(
            {row["external_id"] for row in rows["items"]}, {"100", "101", "102"}
        )
        self.assertTrue(
            all(
                (
                    row["sale_price"] is None and row["quantity"] is None
                    for row in rows["items"]
                )
            )
        )
        progress = await self.request(
            "GET", f"/connections/{connection['connection_id']}/initialization"
        )
        self.assertEqual(progress["processed"], 3)

    async def test_prom_sale_prices_persist_and_clear_after_discount_changes(
        self,
    ) -> None:
        """Worker сохраняет обе скидки; повторный импорт очищает истёкшую акцию."""
        today = datetime.now(ZoneInfo("Europe/Kyiv")).date()
        self.transport.prom_discount = {
            "type": "amount",
            "value": 10,
            "date_start": (today - timedelta(days=1)).strftime("%d.%m.%Y"),
            "date_end": (today + timedelta(days=1)).strftime("%d.%m.%Y"),
        }
        _, connection = await self.create("prom")
        await self.drain()
        route = f"/connections/{connection['connection_id']}"
        initial = await self.request("GET", route + "/publications")
        self.assertEqual(initial["total"], 3)
        for row in initial["items"]:
            self.assertEqual(Decimal(row["price"]), Decimal("99.99"))
            self.assertEqual(Decimal(row["sale_price"]), Decimal("89.99"))
            self.assertNotIn("sale_price_semantics_unverified", row["warnings"])
        for discount, expected in (
            ({**self.transport.prom_discount, "type": "percent"}, Decimal("89.991")),
            (
                {
                    **self.transport.prom_discount,
                    "date_end": (today - timedelta(days=1)).strftime("%d.%m.%Y"),
                },
                None,
            ),
            (
                {
                    **self.transport.prom_discount,
                    "date_start": (today + timedelta(days=1)).strftime("%d.%m.%Y"),
                },
                None,
            ),
            (None, None),
        ):
            self.transport.prom_discount = discount
            await self.request(
                "POST", route + "/initialization", {"request_key": str(uuid4())}, 202
            )
            await self.drain()
            current = await self.request("GET", route + "/publications")
            self.assertEqual(current["total"], 3)
            for row in current["items"]:
                self.assertEqual(
                    (
                        Decimal(row["sale_price"])
                        if row["sale_price"] is not None
                        else None
                    ),
                    expected,
                )
                self.assertEqual(Decimal(row["price"]), Decimal("99.99"))
                self.assertNotIn("invalid_sale_price", row["warnings"])

    async def test_manifest_settings_policy_applies_to_create_and_update(self) -> None:
        """HTTP create и PATCH не обходят фиксированные языки и валюту manifest."""
        for kind, invalid in (
            ("woocommerce", [(("uk", "ru"), "UAH"), (("uk",), None)]),
            (
                "prom",
                [
                    (("uk",), "UAH"),
                    (("ru", "en"), "UAH"),
                    (("ru",), "USD"),
                    (("ru",), None),
                ],
            ),
        ):
            channel = await self.request(
                "POST", "", {"name": "Policy", "platform_kind": kind}, 201
            )
            endpoint = (
                "https://shop.example"
                if kind == "woocommerce"
                else "https://my.prom.ua"
            )
            credentials = (
                {"consumer_key": "key", "consumer_secret": "secret"}
                if kind == "woocommerce"
                else {"token": "token"}
            )
            for locales, currency in invalid:
                with self.subTest(kind=kind, locales=locales, currency=currency):
                    await self.request(
                        "POST",
                        f"/{channel['channel_id']}/connection",
                        {
                            "revision": channel["revision"],
                            "credentials": credentials,
                            "endpoint": endpoint,
                            "settings": {"locales": locales, "currency": currency},
                        },
                        422,
                    )
            valid_locales = ["uk"] if kind == "woocommerce" else ["ru", "uk"]
            saved = await self.request(
                "POST",
                f"/{channel['channel_id']}/connection",
                {
                    "revision": channel["revision"],
                    "credentials": credentials,
                    "endpoint": endpoint,
                    "settings": {"locales": valid_locales, "currency": "UAH"},
                },
                201,
            )
            for locales, currency in invalid:
                with self.subTest(
                    kind=kind, locales=locales, currency=currency, action="update"
                ):
                    await self.request(
                        "PATCH",
                        f"/{channel['channel_id']}/connection",
                        {
                            "revision": saved["revision"],
                            "endpoint": endpoint,
                            "settings": {"locales": locales, "currency": currency},
                        },
                        422,
                    )
            current = await self.request("GET", f"/{channel['channel_id']}/connection")
            self.assertEqual(current["settings"]["locales"], valid_locales)
            self.assertEqual(current["settings"]["currency"], "UAH")

    async def test_auth_csrf_validation_and_secret_redaction(self) -> None:
        """Контракты не принимают tenant/actor из body и не возвращают secret inputs."""
        response = await self.client.post(
            "/api/console/channels", json={"name": "Test", "platform_kind": "prom"}
        )
        self.assertEqual(response.status_code, 403)
        self.app.dependency_overrides[get_authorization_service] = lambda: type(
            "Denied", (), {"can": AsyncMock(return_value=False)}
        )()
        response = await self.client.get("/api/console/channels")
        self.assertEqual(response.status_code, 403)
        self.app.dependency_overrides.pop(get_authorization_service)
        channel = await self.request(
            "POST", "", {"name": "Test", "platform_kind": "prom"}, 201
        )
        response = await self.client.post(
            f"/api/console/channels/{channel['channel_id']}/connection",
            headers=self.headers,
            json={
                "revision": 1,
                "credentials": {"token": {"private-token": "value"}},
                "endpoint": "https://my.prom.ua",
                "settings": {"locales": ["uk"]},
            },
        )
        self.assertEqual(response.status_code, 422)
        self.assertNotIn("private-token", response.text)
        await self.request(
            "POST",
            "",
            {"name": "Bad", "platform_kind": "prom", "tenant_id": str(self.other)},
            422,
        )

    async def test_concurrent_connection_creation_and_sql_constraint(self) -> None:
        """Ровно один concurrent create проходит; архив не освобождает slot."""
        channel = await self.request(
            "POST", "", {"name": "Test", "platform_kind": "prom"}, 201
        )
        body = {
            "revision": 1,
            "credentials": {"token": "token"},
            "endpoint": "https://my.prom.ua",
            "settings": {"locales": ["ru"], "currency": "UAH"},
        }
        path = f"/api/console/channels/{channel['channel_id']}/connection"
        responses = await asyncio.gather(
            *(self.client.post(path, headers=self.headers, json=body) for _ in range(2))
        )
        self.assertEqual(
            sorted((response.status_code for response in responses)), [201, 409]
        )
        async with self.session() as session:
            self.assertEqual(
                await session.scalar(select(func.count()).select_from(ConnectionModel)),
                1,
            )
            row = (
                (await session.execute(select(ConnectionModel.__table__)))
                .mappings()
                .one()
            )
        async with self.session() as session:
            with self.assertRaises(IntegrityError):
                await session.execute(
                    insert(ConnectionModel).values(
                        **{**dict(row), "id": uuid4(), "resource_key": None}
                    )
                )
                await session.flush()
            await session.rollback()

    async def test_verification_failure_does_not_initialize(self) -> None:
        """Ошибочные права оставляют подключение исправляемым без ложного успеха."""
        channel, _ = await self.create()
        self.transport.denied = True
        await self.drain()
        details = await self.request("GET", f"/{channel['channel_id']}/connection")
        self.assertEqual(details["verification_status"], "error")
        self.assertEqual(details["reason_code"], "permission_denied")
        async with self.session() as session:
            self.assertEqual(
                await session.scalar(select(func.count()).select_from(SyncRunModel)), 0
            )

    async def test_failed_page_keeps_rows_and_manual_retry_continues(self) -> None:
        """Отказ поздней страницы сохраняет строки; новый request key продолжает checkpoint."""
        _, connection = await self.create()
        self.transport.fail_page = True
        await self.drain()
        before = await self.request(
            "GET", f"/connections/{connection['connection_id']}/publications"
        )
        self.assertEqual(before["total"], 4)
        progress = await self.request(
            "GET", f"/connections/{connection['connection_id']}/initialization"
        )
        self.assertEqual(progress["status"], "partial")
        self.transport.fail_page = False
        key = str(uuid4())
        first = await self.request(
            "POST",
            f"/connections/{connection['connection_id']}/initialization",
            {"request_key": key},
            202,
        )
        replay = await self.request(
            "POST",
            f"/connections/{connection['connection_id']}/initialization",
            {"request_key": key},
            202,
        )
        self.assertEqual(first["run_id"], replay["run_id"])
        await self.drain()
        after = await self.request(
            "GET", f"/connections/{connection['connection_id']}/publications"
        )
        self.assertEqual(after["total"], 5)
        progress = await self.request(
            "GET", f"/connections/{connection['connection_id']}/initialization"
        )
        self.assertEqual(progress["processed"], 5)

    async def test_pause_discards_prepared_result_and_resume_recovers(self) -> None:
        """Пауза во время сети меняет generation и запрещает apply/следующие шаги."""
        channel, connection = await self.create()
        await self.deliver((await self.claim())[0])
        page = (await self.claim())[0]

        async def pause() -> None:
            current = await self.request("GET", f"/{channel['channel_id']}")
            await self.request(
                "POST",
                f"/{channel['channel_id']}/connection/pause",
                {"revision": current["revision"]},
                204,
            )

        self.transport.callback = pause
        await self.deliver(page)
        rows = await self.request(
            "GET", f"/connections/{connection['connection_id']}/publications"
        )
        self.assertEqual(rows["total"], 0)
        progress = await self.request(
            "GET", f"/connections/{connection['connection_id']}/initialization"
        )
        self.assertEqual(progress["status"], "cancelled")
        current = await self.request("GET", f"/{channel['channel_id']}")
        await self.request(
            "POST",
            f"/{channel['channel_id']}/connection/resume",
            {"revision": current["revision"]},
            204,
        )
        await self.drain()
        self.assertEqual(
            (
                await self.request(
                    "GET", f"/connections/{connection['connection_id']}/publications"
                )
            )["total"],
            5,
        )

    async def test_lost_lease_rolls_back_publications_and_next_job(self) -> None:
        """Потеря lease между HTTP и apply откатывает всю порцию и продолжение."""
        _, connection = await self.create()
        await self.deliver((await self.claim())[0])
        page = (await self.claim())[0]

        async def lose_lease() -> None:
            async with self.sessions() as session:
                await session.execute(
                    update(ScheduledJobModel)
                    .where(ScheduledJobModel.id == page.id)
                    .values(lock_token="replacement")
                )
                await session.commit()

        self.transport.callback = lose_lease
        with self.assertRaises(ScheduledJobDeferred):
            await self.page_worker.handle(page)
        async with self.session() as session:
            self.assertEqual(
                await session.scalar(
                    select(func.count()).select_from(ExternalPublicationModel)
                ),
                0,
            )
            run = (
                await session.execute(
                    select(SyncRunModel.sequence, SyncRunModel.processed)
                )
            ).one()
            self.assertEqual(tuple(run), (0, 0))

    async def test_tenant_isolation_and_no_network_on_queries(self) -> None:
        """Чтение списка локально; IDs чужого tenant не раскрывают публикации."""
        _, connection = await self.create()
        await self.drain()
        before = len(self.transport.calls)
        await self.request(
            "GET",
            f"/connections/{connection['connection_id']}/publications?search=SAME&stock_status=out_of_stock",
        )
        self.assertEqual(len(self.transport.calls), before)
        old = self.app.state.test_context
        self.app.state.test_context = replace(
            old,
            principal=Principal(str(self.actor), str(self.other), "test", ("member",)),
        )
        await self.request(
            "GET",
            f"/connections/{connection['connection_id']}/publications",
            status=404,
        )
        self.app.state.test_context = old

    async def test_network_runs_outside_sql_transaction(self) -> None:
        """Во время GET worker удерживает admission, но не idle SQL transaction."""
        await self.create()

        async def inspect_transactions() -> None:
            async with self.engine.connect() as connection:
                count = await connection.scalar(
                    text(
                        "SELECT count(*) FROM pg_stat_activity WHERE datname=current_database() AND state='idle in transaction'"
                    )
                )
                self.assertEqual(count, 0)

        self.transport.callback = inspect_transactions
        await self.drain()

    async def test_migration_roundtrip_and_autogenerate_drift(self) -> None:
        """Upgrade/downgrade/upgrade согласованы с metadata и не трогают соседей."""
        schema = self.schemas[self.tenant]
        async with self.engine.begin() as connection:
            await TenantMigrator().downgrade(connection, schema, "0027_remove_channels")
            await TenantMigrator().upgrade(connection, schema)

            def compare(sync: object) -> list:
                """Сравнивает только таблицы Channels в tenant search_path."""
                sync.execute(text(f'SET LOCAL search_path TO "{schema}"'))
                original = sync.dialect.default_schema_name
                sync.dialect.default_schema_name = schema
                try:
                    metadata = migration_metadata()
                    context = MigrationContext.configure(
                        sync,
                        opts={
                            "compare_type": True,
                            "compare_server_default": True,
                            "include_object": lambda obj, name, kind, reflected, compare_to: kind
                            != "table"
                            or name
                            in (
                                "channels",
                                "channel_connections",
                                "channel_sync_runs",
                                "channel_external_publications",
                                "channel_product_representations",
                                "channel_external_bindings",
                                "channel_catalog_creation_requests",
                            ),
                        },
                    )
                    return compare_metadata(context, metadata)
                finally:
                    sync.dialect.default_schema_name = original

            drift = await connection.run_sync(compare)
            self.assertEqual(drift, [])

    async def test_empty_source_and_not_started_are_explicit(self) -> None:
        """Пустой доступный источник завершается, отсутствие run не является ошибкой."""
        _, connection = await self.create()
        progress = await self.request(
            "GET", f"/connections/{connection['connection_id']}/initialization"
        )
        self.assertEqual(progress["status"], "not_started")
        self.assertFalse(progress["read_complete"])
        self.transport.empty = True
        await self.drain()
        progress = await self.request(
            "GET", f"/connections/{connection['connection_id']}/initialization"
        )
        self.assertTrue(progress["read_complete"])
        self.assertEqual(progress["processed"], 0)
        self.assertFalse(progress["recovery_required"])

    async def test_terminal_background_job_can_be_recovered(self) -> None:
        """Исчерпание shared retry не оставляет initialization навсегда активным."""
        _, connection = await self.create()
        await self.deliver((await self.claim())[0])
        progress = await self.request(
            "GET", f"/connections/{connection['connection_id']}/initialization"
        )
        async with self.sessions() as session:
            await session.execute(
                update(ScheduledJobModel)
                .where(ScheduledJobModel.id == UUID(progress["job_id"]))
                .values(status="failed")
            )
            await session.commit()
        progress = await self.request(
            "GET", f"/connections/{connection['connection_id']}/initialization"
        )
        self.assertTrue(progress["recovery_required"])
        await self.request(
            "POST",
            f"/connections/{connection['connection_id']}/initialization",
            {"request_key": str(uuid4())},
            202,
        )
        await self.drain()
        progress = await self.request(
            "GET", f"/connections/{connection['connection_id']}/initialization"
        )
        self.assertTrue(progress["read_complete"])
        self.assertEqual(progress["processed"], 5)

    async def test_commit_failure_rolls_back_and_retry_is_safe(self) -> None:
        """Сбой commit не оставляет ни строк, ни сдвинутого checkpoint, ни продолжения."""
        _, connection = await self.create()
        await self.deliver((await self.claim())[0])
        page = (await self.claim())[0]
        original = UnitOfWork.commit
        calls = 0

        async def fail_apply(uow: UnitOfWork) -> None:
            """Оставляет prepare успешным и отказывает на фиксации apply."""
            nonlocal calls
            calls += 1
            if calls == 2:
                raise RuntimeError("simulated_commit_failure")
            await original(uow)

        with patch.object(UnitOfWork, "commit", fail_apply):
            with self.assertRaisesRegex(RuntimeError, "simulated_commit_failure"):
                await self.page_worker.handle(page)
        async with self.session() as session:
            self.assertEqual(
                await session.scalar(
                    select(func.count()).select_from(ExternalPublicationModel)
                ),
                0,
            )
            self.assertEqual(await session.scalar(select(SyncRunModel.sequence)), 0)
        async with self.sessions() as session:
            self.assertEqual(
                await session.scalar(
                    select(func.count())
                    .select_from(ScheduledJobModel)
                    .where(
                        ScheduledJobModel.tenant_id == self.tenant,
                        ScheduledJobModel.job_type == PAGE_JOB,
                    )
                ),
                1,
            )
        await self.deliver(page)
        await self.drain()
        self.assertEqual(
            (
                await self.request(
                    "GET", f"/connections/{connection['connection_id']}/publications"
                )
            )["total"],
            5,
        )

    async def test_duplicate_verified_identity_is_rejected(self) -> None:
        """Два Channels не получают управление одним ресурсом даже при concurrent verify."""
        first, _ = await self.create()
        second, _ = await self.create()
        jobs = await self.claim()
        await asyncio.gather(*(self.deliver(job) for job in jobs))
        details = [
            await self.request("GET", f"/{channel['channel_id']}/connection")
            for channel in (first, second)
        ]
        self.assertEqual(
            sorted((item["verification_status"] for item in details)),
            ["error", "verified"],
        )
        self.assertEqual(
            next((item for item in details if item["verification_status"] == "error"))[
                "reason_code"
            ],
            "resource_identity_in_use",
        )
        await self.drain()

    async def test_credentials_can_be_corrected_while_paused(self) -> None:
        """Настройки paused Connection сохраняются без HTTP; resume проверяет кандидата."""
        channel, connection = await self.create()
        await self.drain()
        current = await self.request("GET", f"/{channel['channel_id']}")
        await self.request(
            "POST",
            f"/{channel['channel_id']}/connection/pause",
            {"revision": current["revision"]},
            204,
        )
        current = await self.request("GET", f"/{channel['channel_id']}")
        changed = await self.request(
            "PATCH",
            f"/{channel['channel_id']}/connection",
            {
                "revision": current["revision"],
                "credentials": {
                    "consumer_key": "replacement",
                    "consumer_secret": "new-secret",
                },
                "endpoint": "https://shop.example",
                "settings": {"locales": ["uk"], "currency": "UAH"},
            },
        )
        self.assertIsNone(changed["verification_job_id"])
        current = await self.request("GET", f"/{channel['channel_id']}/connection")
        self.assertEqual(current["verification_status"], "unverified")
        self.assertTrue(current["candidate_present"])
        await self.request(
            "POST",
            f"/{channel['channel_id']}/connection/resume",
            {"revision": current["revision"]},
            204,
        )
        await self.drain()
        current = await self.request("GET", f"/{channel['channel_id']}/connection")
        self.assertEqual(current["verification_status"], "verified")
        self.assertEqual(current["connection_id"], connection["connection_id"])
        self.assertFalse(current["candidate_present"])
        async with self.session() as session:
            ciphertext = await session.scalar(
                select(ConnectionModel.credentials_ciphertext)
            )
            self.assertNotIn("new-secret", ciphertext)
        await self.request(
            "PATCH",
            f"/{channel['channel_id']}/connection",
            {
                "revision": current["revision"],
                "endpoint": "https://another.example",
                "settings": {"locales": ["uk"], "currency": "UAH"},
            },
            409,
        )

    async def test_manual_refresh_keeps_catalog_and_publication_ids(self) -> None:
        """Новый полный обход обновляет observed, не трогая существующие Catalog значения/audit."""
        from test.catalog_support import initialize_catalog
        from src.modules.catalog.infrastructure.persistence.models.catalog_item import (
            CatalogItemModel,
        )
        from src.modules.catalog.infrastructure.persistence.models.product_type import (
            ProductTypeModel,
        )

        async with self.session() as session:
            await initialize_catalog(
                session, EntityIdVO(self.tenant), EntityIdVO(self.actor)
            )
            type_id = await session.scalar(
                select(ProductTypeModel.id).where(ProductTypeModel.code == "default")
            )
            await session.execute(
                insert(CatalogItemModel).values(
                    id=uuid4(),
                    kind="simple",
                    product_type_id=type_id,
                    status="draft",
                    sku="CANONICAL",
                    revision=1,
                    virtual=False,
                    regular_price=Decimal("42.25"),
                    sale_price=Decimal("40"),
                    currency="UAH",
                    manage_stock=True,
                    stock_quantity=7,
                    stock_status=None,
                    backorders="no",
                    created_by=self.actor,
                    updated_by=self.actor,
                )
            )
            before = await session.scalar(
                text(
                    "SELECT to_jsonb(t) FROM "
                    + self.schemas[self.tenant]
                    + ".catalog_item t"
                )
            )
        _, connection = await self.create()
        await self.drain()
        previous = await self.request(
            "GET", f"/connections/{connection['connection_id']}/publications"
        )
        old_run = await self.request(
            "GET", f"/connections/{connection['connection_id']}/initialization"
        )
        self.transport.price = "199.123456789012"
        refreshed = await self.request(
            "POST",
            f"/connections/{connection['connection_id']}/initialization",
            {"request_key": str(uuid4())},
            202,
        )
        self.assertNotEqual(refreshed["run_id"], old_run["run_id"])
        await self.drain()
        latest = await self.request(
            "GET", f"/connections/{connection['connection_id']}/publications"
        )
        self.assertEqual(
            {item["publication_id"] for item in previous["items"]},
            {item["publication_id"] for item in latest["items"]},
        )
        row = next((item for item in latest["items"] if item["external_id"] == "10"))
        self.assertEqual(Decimal(row["price"]), Decimal("199.123456789012"))
        self.assertEqual(row["observed_revision"], 2)
        progress = await self.request(
            "GET", f"/connections/{connection['connection_id']}/initialization"
        )
        self.assertEqual(progress["processed"], 5)
        async with self.session() as session:
            after = await session.scalar(
                text(
                    "SELECT to_jsonb(t) FROM "
                    + self.schemas[self.tenant]
                    + ".catalog_item t"
                )
            )
        self.assertEqual(after, before)

    async def test_coalesced_request_replay_does_not_refresh_completed_run(
        self,
    ) -> None:
        """Ключ ручного запроса во время auto run остаётся закреплён после завершения."""
        _, connection = await self.create()
        await self.deliver((await self.claim())[0])
        key = str(uuid4())
        accepted = await self.request(
            "POST",
            f"/connections/{connection['connection_id']}/initialization",
            {"request_key": key},
            202,
        )
        await self.drain()
        completed = await self.request(
            "POST",
            f"/connections/{connection['connection_id']}/initialization",
            {"request_key": key},
            202,
        )
        self.assertEqual(accepted["run_id"], completed["run_id"])
        self.assertEqual(completed["status"], "partial")
        self.assertEqual(await self.claim(), [])

    async def test_settings_migration_roundtrip_preserves_existing_observation(
        self,
    ) -> None:
        """0028 → 0029 переносит данные без сброса настроек и не трогает observed."""
        channel, connection = await self.create()
        await self.drain()
        schema = self.schemas[self.tenant]
        async with self.engine.begin() as connection_db:
            migrator = TenantMigrator()
            await migrator.downgrade(connection_db, schema, "0028_channels_core")

            def old_settings(sync_connection) -> None:
                """Добавляет исходные значения непосредственно в схему прежнего релиза."""
                sync_connection.exec_driver_sql(
                    f"UPDATE \"{schema}\".channel_connections SET locales='[\"uk\"]'::jsonb, currency='UAH'"
                )

            await connection_db.run_sync(old_settings)
            await migrator.upgrade(connection_db, schema)
            row = (
                await connection_db.execute(
                    text(f'SELECT settings FROM "{schema}".channel_connections')
                )
            ).scalar_one()
            self.assertEqual(row, {"locales": ["uk"], "currency": "UAH"})
            columns = set(
                (
                    await connection_db.execute(
                        text(
                            "SELECT column_name FROM information_schema.columns WHERE table_schema=:schema AND table_name='channel_external_publications'"
                        ),
                        {"schema": schema},
                    )
                ).scalars()
            )
            self.assertNotIn("core_version", columns)
            self.assertEqual(
                (
                    await connection_db.execute(
                        text(
                            f'SELECT count(*) FROM "{schema}".channel_external_publications'
                        )
                    )
                ).scalar_one(),
                5,
            )
            await migrator.downgrade(connection_db, schema, "0028_channels_core")
            row = (
                await connection_db.execute(
                    text(f'SELECT locales,currency FROM "{schema}".channel_connections')
                )
            ).one()
            self.assertEqual(tuple(row), (["uk"], "UAH"))
            self.assertEqual(
                (
                    await connection_db.execute(
                        text(
                            f'SELECT min(core_version) FROM "{schema}".channel_external_publications'
                        )
                    )
                ).scalar_one(),
                1,
            )
            await migrator.upgrade(connection_db, schema)
        current = await self.request("GET", f"/{channel['channel_id']}/connection")
        self.assertEqual(current["settings"], {"locales": ["uk"], "currency": "UAH"})
        self.assertNotIn("locales", current)
        self.assertNotIn("currency", current)
        await self.request(
            "POST",
            f"/{channel['channel_id']}/connection",
            {
                "revision": current["revision"],
                "settings": {
                    "endpoint": "https://shop.example",
                    "locales": ["uk"],
                    "currency": "UAH",
                },
                "credentials": {"consumer_key": "key", "consumer_secret": "secret"},
            },
            422,
        )

    async def test_plugin_specific_settings_roundtrip_without_new_columns(self) -> None:
        """Новый плагин сохраняет дополнительное поле через общий API и JSONB."""
        from test.test_channels_manifest import ExtendedFactory
        from src.modules.channels.infrastructure.plugin.registry import PluginRegistry
        from src.modules.channels.presentation.depends.plugin_registry import (
            get_plugin_registry,
        )

        self.app.dependency_overrides[get_plugin_registry] = lambda: PluginRegistry(
            (ExtendedFactory(),)
        )
        channel = await self.request(
            "POST", "", {"name": "Extended", "platform_kind": "custom-platform"}, 201
        )
        created = await self.request(
            "POST",
            f"/{channel['channel_id']}/connection",
            {
                "revision": channel["revision"],
                "endpoint": "https://shop.example",
                "settings": {"locales": ["uk"], "currency": "UAH", "batch_size": 250},
                "credentials": {"consumer_key": "key", "consumer_secret": "secret"},
            },
            201,
        )
        current = await self.request("GET", f"/{channel['channel_id']}/connection")
        self.assertEqual(current["settings"]["batch_size"], 250)
        async with self.session() as session:
            row = (
                await session.execute(
                    select(ConnectionModel.settings).where(
                        ConnectionModel.id == UUID(created["connection_id"])
                    )
                )
            ).scalar_one()
            self.assertEqual(row, current["settings"])
