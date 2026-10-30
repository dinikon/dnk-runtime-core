"""HTTP, worker, миграция и конкурентные страницы на отдельной PostgreSQL."""

import asyncio
from dataclasses import replace
from datetime import UTC, datetime, timedelta
import unittest
from uuid import UUID, uuid4
from sqlalchemy import delete, select, update

from test import test_channels_postgres as support
from test.test_channels import FixtureHttp
from test.test_channels_publications import PageHttp, fixture
from src.config import dnk_config
from src.modules.channels.application.error import VerificationFailure
from src.modules.channels.infrastructure.persistence.models.external_publication import (
    ExternalPublicationModel,
)
from src.modules.channels.infrastructure.persistence.models.sync_run import SyncRunModel
from src.modules.channels.infrastructure.persistence.models.connection import (
    ConnectionModel,
)
from src.modules.channels.infrastructure.registry import InstalledPlatforms
from src.modules.channels.presentation.sync_run.jobs.sync_publications import (
    ChannelsSyncPublicationsJobHandler,
)
from src.modules.shared.infrastructure.jobs.scheduled_job_model import ScheduledJobModel
from src.modules.shared.infrastructure.jobs.sqlalchemy_scheduled_job_repository import (
    SqlAlchemyScheduledJobRepository,
)
from src.modules.shared.domain.jobs.scheduled_job import ScheduledJob
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_connection import (
    bind_tenant_schema,
)


class ChannelPublicationPostgresTests(support.ChannelsPostgresTests):
    """Переиспользует изолированные tenant-схемы и реальную HTTP-сборку."""

    async def verified(self, kind: str = "prom", settings: dict | None = None) -> dict:
        """Создаёт и верифицирует подключение, как внешний Shared Worker."""
        if kind == "prom":
            created = await self.create()
            response = {"groups": [{"id": 7101, "parent_group_id": None}]}
        else:
            endpoint = (
                "https://shop.example"
                if kind == "woocommerce"
                else "https://api-seller.rozetka.com.ua"
            )
            credentials = (
                {"consumer_key": "ck-test", "consumer_secret": "cs-test"}
                if kind == "woocommerce"
                else {"token": "private-rozetka"}
            )
            if settings is None:
                settings = (
                    {"currency": "USD", "locale": "en"} if kind == "woocommerce" else {}
                )
            result = await self.client.post(
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
            self.assertEqual(result.status_code, 201, result.text)
            created = result.json()
            response = (
                {"environment": {"site_url": endpoint}}
                if kind == "woocommerce"
                else {"success": True, "content": {"market": {"id": 1086}}}
            )
        job = (await self.claim())[0]
        await self.worker(FixtureHttp([response])).handle(job)
        async with self.sessions() as session:
            await SqlAlchemyScheduledJobRepository(session).mark_done(
                job_id=job.id, lock_token=job.lock_token, completed_at=datetime.now(UTC)
            )
            await session.commit()
        return created

    async def sync_job(self) -> ScheduledJob:
        """Выдаёт текущий шаг публикаций с настоящим lease."""
        async with self.sessions() as session:
            now = datetime.now(UTC)
            jobs = await SqlAlchemyScheduledJobRepository(session).claim_due_jobs(
                limit=20,
                now=now,
                locked_until=now + timedelta(minutes=5),
                lock_token=str(uuid4()),
            )
            await session.commit()
        return next(job for job in jobs if job.job_type == "channels.sync_publications")

    def sync_worker(self, http: PageHttp) -> ChannelsSyncPublicationsJobHandler:
        """Подменяет только HTTP, оставляя Domain, SQL и UoW настоящими."""
        return ChannelsSyncPublicationsJobHandler(
            self.sessions, platforms=InstalledPlatforms(http), cipher=self.cipher
        )

    async def sync_step(self, responses: list) -> None:
        """Выполняет шаг и подтверждает его внешним Shared Worker."""
        job = await self.sync_job()
        await self.sync_worker(PageHttp(responses)).handle(job)
        async with self.sessions() as session:
            await SqlAlchemyScheduledJobRepository(session).mark_done(
                job_id=job.id, lock_token=job.lock_token, completed_at=datetime.now(UTC)
            )
            await session.commit()

    async def test_automatic_prom_sync_cards_replay_and_noop_revision(self) -> None:
        """Включает основной товар в карточку и не применяет повторную доставку."""
        created = await self.verified()
        runs = await self.rows(SyncRunModel)
        self.assertEqual(len(runs), 1)
        response = await self.client.post(
            self.root + "/" + created["id"] + "/sync-runs", headers=self.headers
        )
        self.assertEqual(response.status_code, 202, response.text)
        self.assertEqual(response.json()["id"], str(runs[0]["id"]))
        job = await self.sync_job()
        await asyncio.gather(
            *(
                self.sync_worker(PageHttp([fixture("prom-products.json")])).handle(job)
                for _ in range(2)
            )
        )
        rows = await self.rows(ExternalPublicationModel)
        self.assertEqual(len(rows), 2)
        root, child = sorted(rows, key=lambda row: row["external_id"])
        self.assertEqual(child["parent_id"], root["id"])
        self.assertEqual(root["normalized_data"]["currency"], "UAH")
        self.assertEqual(root["raw_data"]["currency"], "USD")
        completed = (await self.rows(SyncRunModel))[0]
        self.assertEqual(
            (completed["status"], completed["processed_count"]), ("completed", 2)
        )
        base = self.root + "/" + created["id"] + "/publications"
        listing = await self.client.get(base, params={"search": "BLACK-L"})
        self.assertEqual(listing.status_code, 200, listing.text)
        self.assertEqual(listing.json()["total"], 1)
        self.assertEqual(len(listing.json()["items"][0]["items"]), 2)
        detail = await self.client.get(
            base + "/" + str(child["id"]), params={"locale": "ru"}
        )
        self.assertEqual(detail.status_code, 200, detail.text)
        self.assertEqual(
            detail.json()["card"]["selected_publication_id"], str(child["id"])
        )
        self.assertIsNone(detail.json()["card"]["title"])
        self.assertNotIn("raw_data", detail.text)
        self.assertNotIn("platform_data", detail.text)
        starts = await asyncio.gather(
            *(
                self.client.post(
                    self.root + "/" + created["id"] + "/sync-runs", headers=self.headers
                )
                for _ in range(2)
            )
        )
        self.assertEqual([response.status_code for response in starts], [202, 202])
        self.assertEqual(starts[0].json()["id"], starts[1].json()["id"])
        self.assertEqual(len(await self.rows(SyncRunModel)), 2)
        await self.sync_step([fixture("prom-products.json")])
        again = await self.rows(ExternalPublicationModel)
        self.assertEqual(
            {row["external_id"]: (row["id"], row["revision"]) for row in again},
            {row["external_id"]: (row["id"], 1) for row in rows},
        )
        self.assertEqual(await self.rows(ExternalPublicationModel, self.other), [])
        await self.client.post(
            self.root + "/" + created["id"] + "/connection/verify", headers=self.headers
        )
        verification = (await self.claim())[0]
        await self.worker(
            FixtureHttp([{"groups": [{"id": 7101, "parent_group_id": None}]}])
        ).handle(verification)
        self.assertEqual(len(await self.rows(SyncRunModel)), 2)

    async def test_woocommerce_multi_step_and_unsupported_types(self) -> None:
        """Читает продукты, вариации и финализирует обход без фиктивной позиции родителя."""
        created = await self.verified("woocommerce")
        await self.sync_step(
            [{"settings": {"currency": "EUR"}}, fixture("woocommerce-products.json")]
        )
        await self.sync_step([fixture("woocommerce-variations.json")])
        await self.sync_step([])
        run = (await self.rows(SyncRunModel))[0]
        self.assertEqual(
            (run["status"], run["processed_count"], run["skipped_count"]),
            ("completed", 7, 3),
        )
        publications = await self.rows(ExternalPublicationModel)
        self.assertEqual(len(publications), 4)
        parent = next(row for row in publications if row["external_id"] == "510")
        result = await self.client.get(
            self.root + "/" + created["id"] + "/publications/" + str(parent["id"])
        )
        self.assertEqual(result.status_code, 200, result.text)
        card = result.json()["card"]
        self.assertEqual(len(card["items"]), 2)
        self.assertNotIn(str(parent["id"]), [item["id"] for item in card["items"]])
        inherited = next(item for item in card["items"] if item["external_id"] == "512")
        self.assertEqual(
            (inherited["quantity"], inherited["currency"], inherited["title"]),
            ("20", "USD", "T-shirt"),
        )

    async def test_rozetka_list_archive_update_one_identity(self) -> None:
        """Архив обновляет ту же позицию, а не создаёт вторую по rz_item_id."""
        await self.verified("rozetka")
        await self.sync_step([fixture("rozetka-products.json")])
        first = (await self.rows(ExternalPublicationModel))[0]
        await self.sync_step([fixture("rozetka-archive.json")])
        rows = await self.rows(ExternalPublicationModel)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["id"], first["id"])
        self.assertEqual(rows[0]["platform_data"]["rz_item_id"], 344560030)
        self.assertEqual((await self.rows(SyncRunModel))[0]["status"], "completed")

    async def test_partial_pages_survive_terminal_error(self) -> None:
        """Фиксирует первую страницу, сохраняя её после окончательного отказа."""
        await self.verified()
        products = [
            {"id": value, "name": str(value), "price": 1, "currency": "UAH"}
            for value in range(300, 200, -1)
        ]
        await self.sync_step([{"products": products}])
        await self.sync_step([VerificationFailure("permission_missing")])
        self.assertEqual(len(await self.rows(ExternalPublicationModel)), 100)
        run = (await self.rows(SyncRunModel))[0]
        self.assertEqual(
            (run["status"], run["processed_count"], run["pages_count"]),
            ("failed", 100, 1),
        )

    async def test_changed_credentials_during_network_invalidate_page(self) -> None:
        """Вызов API не держит блокировку Channel и не переживает замену доступа."""
        created = await self.verified()
        before = await self.detail(created["id"])
        case = self

        class ChangeAccessHttp(PageHttp):
            async def request(self, method: str, url: str, **kwargs: object) -> object:
                """Меняет доступ через отдельную настоящую HTTP-транзакцию."""
                result = await case.client.patch(
                    case.root + "/" + created["id"],
                    headers=case.headers,
                    json={
                        "expected_revision": before["revision"],
                        "credentials": {"token": "replacement"},
                    },
                )
                case.assertEqual(result.status_code, 200, result.text)
                return await super().request(method, url, **kwargs)

        job = await self.sync_job()
        await asyncio.wait_for(
            self.sync_worker(ChangeAccessHttp([fixture("prom-products.json")])).handle(
                job
            ),
            timeout=10,
        )
        self.assertEqual(await self.rows(ExternalPublicationModel), [])
        self.assertEqual((await self.rows(SyncRunModel))[0]["status"], "cancelled")

    async def test_missing_job_recovery_and_local_deletion(self) -> None:
        """Позволяет перезапуск потерянного задания и удаляет все локальные данные."""
        created = await self.verified()
        run = (await self.rows(SyncRunModel))[0]
        async with self.sessions() as session:
            await session.execute(
                delete(ScheduledJobModel).where(
                    ScheduledJobModel.id == run["current_job_id"]
                )
            )
            await session.commit()
        url = self.root + "/" + created["id"]
        latest = await self.client.get(url + "/sync-runs/latest")
        self.assertTrue(latest.json()["sync_run"]["recovery_required"])
        started = await self.client.post(url + "/sync-runs", headers=self.headers)
        self.assertEqual(started.status_code, 202, started.text)
        self.assertNotEqual(started.json()["id"], str(run["id"]))
        await self.sync_step([fixture("prom-products.json")])
        detail = await self.detail(created["id"])
        deleted = await self.client.delete(
            url, headers=self.headers, params={"expected_revision": detail["revision"]}
        )
        self.assertEqual(deleted.status_code, 204, deleted.text)
        self.assertEqual(await self.rows(SyncRunModel), [])
        self.assertEqual(await self.rows(ExternalPublicationModel), [])

    async def test_prom_primary_change_refreshes_known_tree_atomically(self) -> None:
        """Смена основного товара сохраняет UUID и дозагружает старый корень."""
        created = await self.verified()
        await self.sync_step([fixture("prom-products.json")])
        before = {
            row["external_id"]: row for row in await self.rows(ExternalPublicationModel)
        }
        await self.client.post(
            self.root + "/" + created["id"] + "/sync-runs", headers=self.headers
        )
        promoted = dict(
            fixture("prom-child.json")["product"],
            is_variation=False,
            variation_base_id=None,
        )
        demoted = dict(
            fixture("prom-parent.json")["product"],
            is_variation=True,
            variation_base_id=202,
        )
        await self.sync_step([{"products": [promoted]}, {"product": demoted}])
        after = {
            row["external_id"]: row for row in await self.rows(ExternalPublicationModel)
        }
        self.assertEqual(after["202"]["id"], before["202"]["id"])
        self.assertEqual(after["202"]["kind"], "simple")
        self.assertEqual(after["201"]["parent_id"], after["202"]["id"])
        result = await self.client.get(
            self.root
            + "/"
            + created["id"]
            + "/publications/"
            + str(before["201"]["id"])
        )
        self.assertEqual(result.status_code, 200, result.text)
        self.assertEqual(result.json()["card"]["id"], str(before["202"]["id"]))
        self.assertEqual(len(result.json()["card"]["items"]), 2)

    async def test_expired_lease_rejects_received_page(self) -> None:
        """Поздний HTTP-ответ не сохраняет товары после истечения lease."""
        await self.verified()
        job = await self.sync_job()
        case = self

        class ExpireLeaseHttp(PageHttp):
            async def request(self, method: str, url: str, **kwargs: object) -> object:
                """Истекает lease на независимой транзакции во время API-вызова."""
                async with case.sessions() as session:
                    await session.execute(
                        update(ScheduledJobModel)
                        .where(ScheduledJobModel.id == job.id)
                        .values(locked_until=datetime.now(UTC) - timedelta(seconds=1))
                    )
                    await session.commit()
                return await super().request(method, url, **kwargs)

        await self.sync_worker(ExpireLeaseHttp([fixture("prom-products.json")])).handle(
            job
        )
        self.assertEqual(await self.rows(ExternalPublicationModel), [])
        run = (await self.rows(SyncRunModel))[0]
        self.assertEqual((run["processed_count"], run["pages_count"]), (0, 0))

    async def test_transient_failure_retries_same_checkpoint(self) -> None:
        """Временная ошибка оставляет текущий шаг для Shared retry."""
        await self.verified()
        job = await self.sync_job()
        with self.assertRaises(VerificationFailure):
            await self.sync_worker(
                PageHttp([VerificationFailure("rate_limited", retryable=True)])
            ).handle(job)
        run = (await self.rows(SyncRunModel))[0]
        self.assertEqual(run["processed_count"], 0)
        async with self.sessions() as session:
            await SqlAlchemyScheduledJobRepository(session).mark_failed(
                job_id=job.id,
                lock_token=job.lock_token,
                error="rate_limited",
                retry_at=datetime.now(UTC),
                failed_at=datetime.now(UTC),
            )
            await session.commit()
        await self.sync_step([fixture("prom-products.json")])
        run = (await self.rows(SyncRunModel))[0]
        self.assertEqual((run["status"], run["processed_count"]), ("completed", 2))

    async def test_platform_defaults_rename_and_noop_preserve_stock_settings(
        self,
    ) -> None:
        """Пустые настройки платформы нормализуются без перезаписи локальной политики."""
        for kind in ("prom", "woocommerce"):
            created = await self.verified(kind, settings={})
            url = self.root + "/" + created["id"]
            before = await self.detail(created["id"])
            stored = next(
                row
                for row in await self.rows(ConnectionModel)
                if row["channel_id"] == UUID(created["id"])
            )
            stock_settings = {"stock_sync": stored["settings"]["stock_sync"]}
            async with self.engine.begin() as connection:
                await bind_tenant_schema(connection, self.tenant, self.naming)
                await connection.execute(
                    update(ConnectionModel)
                    .where(ConnectionModel.channel_id == UUID(created["id"]))
                    .values(settings=stock_settings)
                )
            detail = await self.detail(created["id"])
            self.assertEqual(detail["config"]["settings"]["currency"], "UAH")
            renamed = await self.client.patch(
                url,
                headers=self.headers,
                json={
                    "expected_revision": before["revision"],
                    "name": "Renamed " + kind,
                    "config": detail["config"],
                },
            )
            self.assertEqual(renamed.status_code, 200, renamed.text)
            after = await self.detail(created["id"])
            self.assertEqual(
                (after["config_revision"], after["verification"]["status"]),
                (1, "verified"),
            )
            self.assertEqual(after["revision"], before["revision"] + 1)
            noop = await self.client.patch(
                url,
                headers=self.headers,
                json={
                    "expected_revision": after["revision"],
                    "name": after["name"],
                    "config": after["config"],
                },
            )
            self.assertEqual(noop.status_code, 200, noop.text)
            self.assertEqual(
                (await self.detail(created["id"]))["revision"], after["revision"]
            )
            rows = await self.rows(ConnectionModel)
            self.assertEqual(
                next(row for row in rows if row["channel_id"] == UUID(created["id"]))[
                    "settings"
                ],
                stock_settings,
            )

    async def test_woo_config_change_fences_page_and_preserves_old_interpretation(
        self,
    ) -> None:
        """Валюта и язык меняют только новые снимки после успешной повторной проверки."""
        created = await self.verified("woocommerce")
        records = [
            {"id": 501, "type": "simple", "name": "Received text", "price": "17.50"}
        ]
        await self.sync_step([{"settings": {"currency": "EUR"}}, records])
        await self.sync_step([])
        before = await self.detail(created["id"])
        url = self.root + "/" + created["id"]
        await self.client.post(url + "/sync-runs", headers=self.headers)
        job = await self.sync_job()
        case = self

        class ChangeSettingsHttp(PageHttp):
            async def request(
                self, method: str, request_url: str, **kwargs: object
            ) -> object:
                """Меняет конфигурацию, пока исходный HTTP-вызов ещё выполняется."""
                if request_url.endswith("system_status"):
                    config = dict(
                        before["config"], settings={"currency": "EUR", "locale": "ru"}
                    )
                    response = await case.client.patch(
                        url,
                        headers=case.headers,
                        json={
                            "expected_revision": before["revision"],
                            "config": config,
                        },
                    )
                    case.assertEqual(response.status_code, 200, response.text)
                return await super().request(method, request_url, **kwargs)

        await self.sync_worker(
            ChangeSettingsHttp([{"settings": {"currency": "EUR"}}, records])
        ).handle(job)
        detail = await self.detail(created["id"])
        self.assertEqual(
            (detail["config_revision"], detail["verification"]["status"]),
            (2, "pending"),
        )
        publications = await self.rows(ExternalPublicationModel)
        self.assertEqual(publications[0]["normalized_data"]["currency"], "USD")
        self.assertEqual(
            publications[0]["normalized_data"]["titles"], {"en": "Received text"}
        )
        listing = await self.client.get(url + "/publications")
        item = listing.json()["items"][0]["items"][0]
        self.assertEqual(
            (item["currency"], item["title"], item["stale_configuration"]),
            ("USD", None, True),
        )
        verification = (await self.claim())[0]
        await self.worker(
            FixtureHttp([{"environment": {"site_url": "https://shop.example"}}])
        ).handle(verification)
        await self.sync_step([{"settings": {"currency": "USD"}}, records])
        await self.sync_step([])
        refreshed = (await self.rows(ExternalPublicationModel))[0]
        self.assertEqual(refreshed["id"], publications[0]["id"])
        self.assertEqual(refreshed["normalized_data"]["currency"], "EUR")
        self.assertEqual(
            refreshed["normalized_data"]["titles"], {"ru": "Received text"}
        )


def load_tests(
    loader: unittest.TestLoader, tests: unittest.TestSuite, pattern: str | None
) -> unittest.TestSuite:
    """Не повторяет унаследованные тесты предыдущего среза."""
    return unittest.TestSuite(
        ChannelPublicationPostgresTests(name)
        for name in ChannelPublicationPostgresTests.__dict__
        if name.startswith("test_")
    )
