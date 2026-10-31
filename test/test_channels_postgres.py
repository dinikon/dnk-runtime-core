"""HTTP, миграция и worker Channels на отдельной PostgreSQL базе."""

import asyncio
import os
import unittest
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from unittest.mock import patch
from uuid import UUID, uuid4
from cryptography.fernet import Fernet
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool
from sqlalchemy.schema import CreateSchema, DropSchema
from src.config import dnk_config
from src.modules.channels.presentation.router import router
from src.modules.channels.presentation.jobs.verify_connection import (
    ChannelsVerifyConnectionJobHandler,
)
from src.modules.channels.infrastructure.registry import InstalledPlatforms
from src.modules.shared.infrastructure.crypto.fernet_cipher import FernetCipher
from src.modules.channels.infrastructure.persistence.models.channel import ChannelModel
from src.modules.channels.infrastructure.persistence.models.connection import (
    ConnectionModel,
)
from src.modules.channels.infrastructure.jobs import SharedVerificationJobs
from src.modules.channels.application.error import VerificationFailure
from src.modules.shared.infrastructure.jobs.scheduled_job_model import ScheduledJobModel
from src.modules.shared.infrastructure.jobs.sqlalchemy_scheduled_job_repository import (
    SqlAlchemyScheduledJobRepository,
)
from src.modules.shared.domain.jobs.scheduled_job import ScheduledJob
from src.modules.tenancy.infrastructure.persistence.tenant import TenantModel
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_migrations import (
    TenantMigrator,
)
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_connection import (
    bind_tenant_schema,
)
from src.modules.tenancy.application.tenant.tenant_schema_naming import (
    TenantSchemaNaming,
)
from src.modules.identity.domain.auth.principal import Principal
from src.modules.identity.domain.auth.request_context import RequestContext
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from test.crm_company_support import company_app
from test.test_channels import FixtureHttp
from src.modules.reference_data.infrastructure.persistence.models.currency import (
    CurrencyModel,
)
from src.modules.reference_data.infrastructure.persistence.models.locale import (
    LocaleModel,
)
from src.modules.reference_data.infrastructure.persistence.models.country import (
    CountryModel,
)
from sqlalchemy.dialects.postgresql import insert as pg_insert

TEST_URL = os.environ.get("TEST_POSTGRES_URL")


@unittest.skipUnless(
    TEST_URL, "Set TEST_POSTGRES_URL to a disposable PostgreSQL database."
)
class ChannelsPostgresTests(unittest.IsolatedAsyncioTestCase):
    """Проверяет HTTP, транзакции, миграцию и гонки worker в tenant-схемах."""

    async def asyncSetUp(self) -> None:
        """Создаёт отдельные tenant-схемы и HTTP-сборку с настоящими UoW и CSRF."""
        self.engine = create_async_engine(TEST_URL, poolclass=NullPool)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        self.tenant, self.other, self.actor = uuid4(), uuid4(), uuid4()
        self.naming = TenantSchemaNaming(dnk_config.SCHEMA_PREFIX)
        self.schemas = [
            self.naming.schema_name(EntityIdVO(value))
            for value in (self.tenant, self.other)
        ]
        async with self.engine.begin() as connection:
            for table in (
                TenantModel.__table__,
                ScheduledJobModel.__table__,
                CountryModel.__table__,
                CurrencyModel.__table__,
                LocaleModel.__table__,
            ):
                await connection.run_sync(
                    lambda c, table=table: table.create(c, checkfirst=True)
                )
            for code in ("UAH", "USD", "EUR"):
                await connection.execute(
                    pg_insert(CurrencyModel)
                    .values(code=code, name=code, minor_units=2, active=True)
                    .on_conflict_do_nothing()
                )
            for code in ("uk", "ru", "en"):
                await connection.execute(
                    pg_insert(LocaleModel)
                    .values(code=code, language_code=code, name=code, active=True)
                    .on_conflict_do_nothing()
                )
            for tenant, schema in zip((self.tenant, self.other), self.schemas):
                await connection.execute(
                    TenantModel.__table__.insert().values(
                        id=tenant,
                        name="Channels test",
                        external_id=str(tenant),
                        status="active",
                    )
                )
                await connection.execute(CreateSchema(schema))
                await TenantMigrator().upgrade(connection, schema)
        self.context = RequestContext(
            Principal(str(self.actor), str(self.tenant), "test-session", ("member",)),
            None,
            None,
            None,
        )
        self.app = company_app(self.sessions, self.context, scoped_connection=True)
        self.app.include_router(router, prefix="/api/console")
        self.cipher = FernetCipher(Fernet.generate_key().decode())
        self.cipher_patch = patch(
            "src.modules.channels.presentation.depends.get_cipher",
            return_value=self.cipher,
        )
        self.cipher_patch.start()
        scheme = "http" if dnk_config.AUTH.allow_insecure_http else "https"
        origin = f"{scheme}://tenant.example"
        self.client = AsyncClient(
            transport=ASGITransport(app=self.app), base_url=origin
        )
        token = (await self.client.get("/csrf")).json()["csrf_token"]
        self.headers = {"Origin": origin, "X-CSRF-Token": token}
        self.root = "/api/console/channels"

    async def asyncTearDown(self) -> None:
        """Удаляет только схемы и задания текущего теста и закрывает соединения."""
        self.cipher_patch.stop()
        await self.client.aclose()
        async with self.engine.begin() as connection:
            for schema in self.schemas:
                await connection.execute(
                    DropSchema(schema, cascade=True, if_exists=True)
                )
            await connection.execute(
                delete(ScheduledJobModel).where(
                    ScheduledJobModel.tenant_id.in_((self.tenant, self.other))
                )
            )
            await connection.execute(
                delete(TenantModel).where(TenantModel.id.in_((self.tenant, self.other)))
            )
        await self.engine.dispose()

    async def rows(self, model: type, tenant: UUID | None = None) -> list:
        """Читает записи заданной модели в выбранном tenant теста."""
        async with self.engine.connect() as connection:
            await bind_tenant_schema(connection, tenant or self.tenant, self.naming)
            statement = select(model.__table__)
            if model is ScheduledJobModel:
                statement = statement.where(model.tenant_id == (tenant or self.tenant))
            return list((await connection.execute(statement)).mappings())

    async def create(self, name: str = "Store", token: str = "test-secret") -> dict:
        """Создаёт Prom-подключение через публичный HTTP-контракт."""
        response = await self.client.post(
            self.root,
            headers=self.headers,
            json={
                "name": name,
                "platform_kind": "prom",
                "config": {
                    "version": 1,
                    "endpoint": "https://my.prom.ua",
                    "settings": {},
                },
                "credentials": {"token": token},
            },
        )
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()

    async def detail(self, identifier: str) -> dict:
        """Читает публичную карточку и проверяет успешность ответа."""
        response = await self.client.get(self.root + "/" + identifier)
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    async def claim(self) -> list[ScheduledJob]:
        """Выдаёт задания worker с действующей lease через Shared Jobs."""
        async with self.sessions() as session:
            now = datetime.now(UTC)
            jobs = await SqlAlchemyScheduledJobRepository(session).claim_due_jobs(
                limit=20,
                now=now,
                locked_until=now + timedelta(minutes=5),
                lock_token="channels-test-worker",
            )
            await session.commit()
            return [job for job in jobs if job.job_type == "channels.verify_connection"]

    def worker(self, http: FixtureHttp) -> ChannelsVerifyConnectionJobHandler:
        """Собирает настоящий обработчик с тестовым HTTP-портом."""
        return ChannelsVerifyConnectionJobHandler(
            self.sessions, platforms=InstalledPlatforms(http), cipher=self.cipher
        )

    async def test_atomic_crud_validation_secrets_csrf_and_tenant_isolation(
        self,
    ) -> None:
        """Сохраняет две части и job; выдаёт только публичные поля и проверяет CSRF."""
        created = await self.create(" Store ")
        detail = await self.detail(created["id"])
        self.assertEqual(detail["name"], "Store")
        self.assertEqual(detail["available_capabilities"], ["verify_connection"])
        connection = (await self.rows(ConnectionModel))[0]
        self.assertNotIn(b"test-secret", connection["encrypted_credentials"])
        self.assertIn(
            b"test-secret", self.cipher.decrypt(connection["encrypted_credentials"])
        )
        self.assertNotIn("test-secret", str(await self.rows(ScheduledJobModel)))
        self.assertNotIn("encrypted_credentials", detail)
        self.assertNotIn("credentials", detail)
        self.assertEqual(len(await self.rows(ChannelModel)), 1)
        self.assertEqual(len(await self.rows(ConnectionModel)), 1)
        self.assertEqual(await self.rows(ChannelModel, self.other), [])
        self.app.state.test_context = replace(
            self.context,
            principal=replace(self.context.principal, tenant_id=str(self.other)),
        )
        self.assertEqual(
            (await self.client.get(self.root + "/" + created["id"])).status_code, 404
        )
        self.app.state.test_context = self.context
        no_csrf = await self.client.post(
            self.root + "/" + created["id"] + "/connection/verify"
        )
        self.assertEqual(no_csrf.status_code, 403)
        for body in (
            {"expected_revision": 1, "credentials": None},
            {"expected_revision": 1, "credentials": {"token": ""}},
            {"expected_revision": 1, "platform_kind": "woocommerce"},
        ):
            response = await self.client.patch(
                self.root + "/" + created["id"], headers=self.headers, json=body
            )
            self.assertEqual(response.status_code, 422)
            self.assertNotIn("input", response.text)
        malformed = await self.client.post(
            self.root,
            headers={**self.headers, "Content-Type": "application/json"},
            content=b'{"credentials":{"token":"never-echo-this-secret"}',
        )
        self.assertEqual(malformed.status_code, 422)
        self.assertNotIn("never-echo", malformed.text)
        for _ in range(2):
            response = await self.client.post(
                self.root + "/" + created["id"] + "/connection/verify",
                headers=self.headers,
            )
            self.assertEqual(
                response.json()["verification_job_id"], created["verification_job_id"]
            )
        self.assertEqual(len(await self.rows(ScheduledJobModel)), 1)

    async def test_schedule_failure_rolls_back_entire_creation(self) -> None:
        """Ошибка постановки задания откатывает и Channel, и credentials."""
        with patch.object(
            SharedVerificationJobs,
            "schedule",
            side_effect=RuntimeError("test-job-failure"),
        ):
            with self.assertRaises(RuntimeError):
                await self.create()
        self.assertEqual(await self.rows(ChannelModel), [])
        self.assertEqual(await self.rows(ConnectionModel), [])
        self.assertEqual(await self.rows(ScheduledJobModel), [])

    async def test_worker_verifies_and_renaming_during_http_does_not_invalidate_snapshot(
        self,
    ) -> None:
        """HTTP-вызов не держит SQL-транзакцию и блокировку корня."""
        created = await self.create()
        jobs = await self.claim()
        entered, release = asyncio.Event(), asyncio.Event()
        outer = self

        class PausedHttp(FixtureHttp):
            """Приостанавливает внешний вызов для воспроизведения конкурентного изменения."""

            async def request(self, method: str, url: str, **kwargs: object) -> object:
                """Возвращает подготовленный ответ без обращения к внешней площадке."""
                entered.set()
                await release.wait()
                return await super().request(method, url, **kwargs)

        http = PausedHttp([{"groups": [{"id": 7, "parent_group_id": None}]}])
        task = asyncio.create_task(self.worker(http).handle(jobs[0]))
        await asyncio.wait_for(entered.wait(), 5)
        response = await asyncio.wait_for(
            self.client.patch(
                self.root + "/" + created["id"],
                headers=self.headers,
                json={"expected_revision": 1, "name": "Renamed"},
            ),
            5,
        )
        self.assertEqual(response.status_code, 200, response.text)
        release.set()
        await asyncio.wait_for(task, 5)
        detail = await self.detail(created["id"])
        self.assertEqual(detail["name"], "Renamed")
        self.assertEqual(detail["verification"]["status"], "verified")
        self.assertEqual(detail["identity"]["key"], "7")
        revision = detail["revision"]
        await self.worker(FixtureHttp([])).handle(jobs[0])
        self.assertEqual((await self.detail(created["id"]))["revision"], revision)

    async def test_credentials_replacement_and_delete_discard_inflight_results(
        self,
    ) -> None:
        """Поздний результат не подтверждает новый доступ и не восстанавливает удалённый канал."""
        for action in ("replace", "delete"):
            created = await self.create(action)
            jobs = await self.claim()
            job = next(j for j in jobs if str(j.payload["channel_id"]) == created["id"])
            entered, release = asyncio.Event(), asyncio.Event()

            class PausedHttp(FixtureHttp):
                """Приостанавливает внешний вызов для воспроизведения конкурентного изменения."""

                async def request(
                    self, method: str, url: str, **kwargs: object
                ) -> object:
                    """Возвращает подготовленный ответ без обращения к внешней площадке."""
                    entered.set()
                    await release.wait()
                    return await super().request(method, url, **kwargs)

            task = asyncio.create_task(
                self.worker(
                    PausedHttp([{"groups": [{"id": 8, "parent_group_id": None}]}])
                ).handle(job)
            )
            await asyncio.wait_for(entered.wait(), 5)
            if action == "replace":
                response = await self.client.patch(
                    self.root + "/" + created["id"],
                    headers=self.headers,
                    json={
                        "expected_revision": 1,
                        "credentials": {"token": "new-secret"},
                    },
                )
            else:
                response = await self.client.delete(
                    self.root + "/" + created["id"],
                    headers=self.headers,
                    params={"expected_revision": 1},
                )
            self.assertIn(response.status_code, (200, 204), response.text)
            release.set()
            await asyncio.wait_for(task, 5)
            if action == "replace":
                detail = await self.detail(created["id"])
                self.assertEqual(detail["config_revision"], 2)
                self.assertEqual(detail["verification"]["status"], "pending")
                self.assertIsNone(detail["identity"])
            else:
                self.assertEqual(
                    (
                        await self.client.get(self.root + "/" + created["id"])
                    ).status_code,
                    404,
                )

    async def test_concurrent_identity_claim_and_delete_releases_resource(self) -> None:
        """У одного магазина ровно один владелец; после удаления claim освобождается."""
        first, second = await self.create("First"), await self.create("Second")
        jobs = await self.claim()
        await asyncio.gather(
            *(
                self.worker(
                    FixtureHttp([{"groups": [{"id": 9, "parent_group_id": None}]}])
                ).handle(job)
                for job in jobs
            )
        )
        details = [await self.detail(first["id"]), await self.detail(second["id"])]
        winner = next(d for d in details if d["verification"]["status"] == "verified")
        loser = next(d for d in details if d["verification"]["status"] == "error")
        self.assertEqual(
            loser["verification"]["error_code"], "resource_already_connected"
        )
        deleted = await self.client.delete(
            self.root + "/" + winner["id"],
            headers=self.headers,
            params={"expected_revision": winner["revision"]},
        )
        self.assertEqual(deleted.status_code, 204)
        requested = await self.client.post(
            self.root + "/" + loser["id"] + "/connection/verify", headers=self.headers
        )
        self.assertEqual(requested.status_code, 202)
        job = (await self.claim())[0]
        await self.worker(
            FixtureHttp([{"groups": [{"id": 9, "parent_group_id": None}]}])
        ).handle(job)
        self.assertEqual(
            (await self.detail(loser["id"]))["verification"]["status"], "verified"
        )

    async def test_lost_lease_recovery_required_and_manual_retry(self) -> None:
        """Не вызывает API без lease и восстанавливает прерванное поколение вручную."""
        created = await self.create()
        job = (await self.claim())[0]
        async with self.sessions() as session:
            await session.execute(
                update(ScheduledJobModel)
                .where(ScheduledJobModel.id == job.id)
                .values(lock_token="another-worker")
            )
            await session.commit()
        http = FixtureHttp([])
        await self.worker(http).handle(job)
        self.assertEqual(http.calls, [])
        async with self.sessions() as session:
            await session.execute(
                update(ScheduledJobModel)
                .where(ScheduledJobModel.id == job.id)
                .values(status="failed")
            )
            await session.commit()
        detail = await self.detail(created["id"])
        self.assertTrue(detail["recovery_required"])
        response = await self.client.post(
            self.root + "/" + created["id"] + "/connection/verify", headers=self.headers
        )
        self.assertEqual(response.status_code, 202)
        self.assertNotEqual(response.json()["verification_job_id"], str(job.id))
        self.assertFalse((await self.detail(created["id"]))["recovery_required"])

    async def test_transient_failure_retries_but_final_attempt_is_saved(self) -> None:
        """Сохраняет pending до исчерпания повторов и фиксирует конечную ошибку."""
        created = await self.create()
        job = (await self.claim())[0]
        with self.assertRaises(VerificationFailure):
            await self.worker(
                FixtureHttp([VerificationFailure("rate_limited", retryable=True)])
            ).handle(job)
        self.assertEqual(
            (await self.detail(created["id"]))["verification"]["status"], "pending"
        )
        await self.worker(
            FixtureHttp([VerificationFailure("rate_limited", retryable=True)])
        ).handle(replace(job, attempts=dnk_config.SCHEDULED_JOBS.max_attempts))
        detail = await self.detail(created["id"])
        self.assertEqual(detail["verification"]["error_code"], "rate_limited")
        self.assertEqual(detail["verification"]["status"], "error")

    async def test_all_platforms_create_and_verify_through_http_and_worker(
        self,
    ) -> None:
        """Пакеты Rozetka/WooCommerce подключены к реальному HTTP/SQL потоку."""
        cases = [
            (
                "rozetka",
                "https://api-seller.rozetka.com.ua",
                {},
                {"token": "test-token"},
                {"success": True, "content": {"id": 11, "market": {"id": 22}}},
                "22",
            ),
            (
                "woocommerce",
                "https://shop.example/wordpress/",
                {},
                {"consumer_key": "ck-test", "consumer_secret": "cs-test"},
                {"environment": {"site_url": "https://shop.example/wordpress/"}},
                "https://shop.example/wordpress",
            ),
        ]
        for kind, endpoint, settings, credentials, result, key in cases:
            response = await self.client.post(
                self.root,
                headers=self.headers,
                json={
                    "name": kind,
                    "platform_kind": kind,
                    "config": {
                        "version": 1,
                        "endpoint": endpoint,
                        "settings": settings,
                    },
                    "credentials": credentials,
                },
            )
            self.assertEqual(response.status_code, 201, response.text)
            created = response.json()
            job = next(
                j
                for j in await self.claim()
                if str(j.payload["channel_id"]) == created["id"]
            )
            await self.worker(FixtureHttp([result])).handle(job)
            detail = await self.detail(created["id"])
            self.assertEqual(detail["verification"]["status"], "verified")
            self.assertEqual(detail["identity"]["key"], key)
            self.assertNotIn("test-password", str(detail))

    async def test_unreadable_credentials_and_missing_key_are_safe(self) -> None:
        """Worker не вызывает API при неправильном ключе, а отсутствие ключа даёт 503."""
        created = await self.create()
        job = (await self.claim())[0]
        http = FixtureHttp([])
        wrong_cipher = FernetCipher(Fernet.generate_key().decode())
        await ChannelsVerifyConnectionJobHandler(
            self.sessions, platforms=InstalledPlatforms(http), cipher=wrong_cipher
        ).handle(job)
        self.assertEqual(http.calls, [])
        detail = await self.detail(created["id"])
        self.assertEqual(detail["verification"]["error_code"], "credentials_unreadable")
        with patch(
            "src.modules.channels.presentation.depends.get_cipher",
            return_value=FernetCipher(None),
        ):
            failed = await self.client.post(
                self.root,
                headers=self.headers,
                json={
                    "name": "new",
                    "platform_kind": "prom",
                    "config": {
                        "version": 1,
                        "endpoint": "https://my.prom.ua",
                        "settings": {},
                    },
                    "credentials": {"token": "must-not-leak"},
                },
            )
            self.assertEqual(failed.status_code, 503)
            self.assertNotIn("must-not-leak", failed.text)
            rename = await self.client.patch(
                self.root + "/" + created["id"],
                headers=self.headers,
                json={
                    "expected_revision": detail["revision"],
                    "name": "Renamed without key",
                },
            )
            self.assertEqual(rename.status_code, 200)
            self.assertEqual(len(await self.rows(ChannelModel)), 1)

    async def test_authorization_and_revision_conflicts_do_not_write(self) -> None:
        """Участник допускается стандартной политикой; явный deny и старая revision защищены."""
        created = await self.create()
        path = self.root + "/" + created["id"]
        response = await self.client.patch(
            path,
            headers=self.headers,
            json={
                "expected_revision": 99,
                "credentials": {"token": "unapplied-secret"},
            },
        )
        self.assertEqual(response.status_code, 409)
        self.assertEqual((await self.detail(created["id"]))["config_revision"], 1)
        response = await self.client.delete(
            path, headers=self.headers, params={"expected_revision": 99}
        )
        self.assertEqual(response.status_code, 409)

        class Deny:
            """Запрещает действие через существующий authorization port."""

            async def can(self, **kwargs: object) -> bool:
                """Возвращает явный отказ политики доступа."""
                return False

        self.app.state.authorization_service = Deny()
        self.assertEqual((await self.client.get(path)).status_code, 403)
        self.assertEqual(
            (
                await self.client.delete(
                    path, headers=self.headers, params={"expected_revision": 1}
                )
            ).status_code,
            403,
        )
        self.assertEqual(len(await self.rows(ChannelModel)), 1)

    async def test_current_schema_contains_only_channels_and_connections(self) -> None:
        """Новый tenant хранит только подключение, сохраняя соседние модули."""
        from sqlalchemy import inspect

        async with self.engine.connect() as connection:
            names = await connection.run_sync(
                lambda c: inspect(c).get_table_names(schema=self.schemas[0])
            )
        self.assertEqual(
            {
                name
                for name in names
                if name == "channels" or name.startswith("channel_")
            },
            {"channels", "channel_connections"},
        )
        self.assertTrue(
            {"catalog_item", "contacts", "crm_deals", "files_registry"} <= set(names)
        )
        created = await self.create()
        self.assertEqual(
            (await self.detail(created["id"]))["verification"]["status"], "pending"
        )
