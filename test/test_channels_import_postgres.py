"""Полная карточка: настоящий HTTP/CSRF, durable jobs, PostgreSQL и MinIO."""

import asyncio
from datetime import UTC, datetime, timedelta
from decimal import Decimal
import os
import unittest
from unittest.mock import patch
from uuid import UUID, uuid4, uuid5
from dataclasses import replace
from sqlalchemy import delete
from src.modules.shared.infrastructure.jobs.scheduled_job_model import ScheduledJobModel
from src.modules.identity.domain.auth.principal import Principal
from sqlalchemy import select, update
from src.config import dnk_config
from src.config.infrastructure.files_config import FilesSettings
from src.modules.channels.presentation.jobs.publication_import import (
    ChannelsPublicationImportJobHandler,
)
from src.modules.channels.infrastructure.jobs import IMPORT_JOB, IMPORT_CLEANUP_JOB
from src.modules.channels.infrastructure.persistence.models.publication_import import (
    PublicationImportModel,
)
from src.modules.channels.infrastructure.persistence.models.external_publication import (
    ExternalPublicationModel,
)
from src.modules.channels.infrastructure.persistence.models.connection import (
    ConnectionModel,
)
from src.modules.channels.presentation.publication_import.assembly import (
    build_publication_import_handlers,
)
from src.modules.channels.application.publication_import.command.cleanup_publication_import.command import (
    CleanupPublicationImportCommand,
)
from src.modules.channels.presentation.depends.plugin_registry import (
    get_plugin_registry,
)
from src.modules.files.infrastructure.assembly import build_files_handlers
from src.modules.files.infrastructure.storage.minio_adapter import MinioStorageAdapter
from src.modules.files.infrastructure.storage.resolver import StorageResolver
from src.modules.files.infrastructure.persistence.models.stored_file import (
    StoredFileModel,
)
from src.modules.files.application.storage_provider.command.register_system_storage.command import (
    RegisterSystemStorageCommand,
)
from src.modules.files.application.bucket.command.provision_system_bucket.command import (
    ProvisionSystemBucketCommand,
)
from src.modules.files.application.bucket.command.purge_tenant_storage.command import (
    PurgeTenantStorageCommand,
)
from src.modules.shared.infrastructure.jobs.sqlalchemy_scheduled_job_repository import (
    SqlAlchemyScheduledJobRepository,
)
from src.modules.shared.domain.jobs.scheduled_job import ScheduledJob
from test import test_channels_bindings_postgres as binding_fixture
from test import test_channels_postgres as base_fixture
from test.channels_import_support import (
    FullPublicationTransport,
    FixtureImageDownloader,
    PNG,
)


@unittest.skipUnless(
    os.environ.get("TEST_POSTGRES_URL") and os.environ.get("TEST_MINIO_ENDPOINT"),
    "Requires disposable PostgreSQL and MinIO",
)
class ChannelsImportPostgresTests(unittest.IsolatedAsyncioTestCase):
    """Проверяет реальные межмодульные записи, повторы, изоляцию и очистку."""

    session = base_fixture.ChannelsPostgresTests.session
    request = base_fixture.ChannelsPostgresTests.request
    create = base_fixture.ChannelsPostgresTests.create
    claim = base_fixture.ChannelsPostgresTests.claim
    drain = base_fixture.ChannelsPostgresTests.drain
    catalog = binding_fixture.ChannelsBindingsPostgresTests.catalog
    imported = binding_fixture.ChannelsBindingsPostgresTests.imported
    item_count = binding_fixture.ChannelsBindingsPostgresTests.item_count

    async def asyncSetUp(self) -> None:
        """Создаёт изолированные tenant-схемы и приватные тестовые бакеты."""
        await binding_fixture.ChannelsBindingsPostgresTests.asyncSetUp(self)
        self.transport = FullPublicationTransport()
        self.transport.price = "123.45"
        self.verify_worker.transport_factory = lambda _: self.transport
        self.page_worker.transport_factory = lambda _: self.transport
        self.downloader = FixtureImageDownloader()
        settings = FilesSettings(
            endpoint=os.environ["TEST_MINIO_ENDPOINT"],
            access_key="channels-import",
            secret_key="channels-import-test-secret",
            secure=False,
        )
        self.adapter = MinioStorageAdapter(settings)
        self.resolver = StorageResolver(
            {("minio", "system_minio"): lambda: self.adapter}
        )
        self.storage_patch = patch(
            "src.modules.files.infrastructure.assembly.get_storage_resolver",
            return_value=self.resolver,
        )
        self.storage_patch.start()
        self.import_worker = ChannelsPublicationImportJobHandler(
            self.sessions,
            transport_factory=lambda _: self.transport,
            downloader=self.downloader,
            storage=self.resolver,
            encryption_key=self.key,
        )
        for tenant in (self.tenant, self.other):
            async with self.session(tenant) as session:
                registration = await build_files_handlers(
                    session, self.resolver
                ).register.execute(RegisterSystemStorageCommand(tenant))
            async with self.session(tenant) as session:
                await build_files_handlers(session, self.resolver).provision.execute(
                    ProvisionSystemBucketCommand(tenant, registration.bucket_id)
                )

    async def asyncTearDown(self) -> None:
        """Удаляет только собственные бакеты и схемы одноразового окружения."""
        for tenant in (self.tenant, self.other):
            async with self.session(tenant) as session:
                await build_files_handlers(session, self.resolver).purge.execute(
                    PurgeTenantStorageCommand(tenant)
                )
        self.storage_patch.stop()
        await base_fixture.ChannelsPostgresTests.asyncTearDown(self)

    async def deliver(self, job: ScheduledJob) -> None:
        """Доставляет новые job types тем же production worker."""
        if job.job_type not in (IMPORT_JOB, IMPORT_CLEANUP_JOB):
            await base_fixture.ChannelsPostgresTests.deliver(self, job)
            return
        await self.import_worker.handle(job)
        async with self.sessions() as session:
            await SqlAlchemyScheduledJobRepository(session).mark_done(
                job_id=job.id, lock_token=job.lock_token, completed_at=datetime.now(UTC)
            )
            await session.commit()

    async def prepare(self, pub: dict) -> dict:
        """Запускает preparation через HTTP и обрабатывает все ограниченные шаги."""
        result = await self.request(
            "POST",
            f"/publications/{pub['publication_id']}/import-preparations",
            {
                "preparation_id": str(uuid4()),
                "expected_observed_revision": pub["observed_revision"],
            },
            202,
        )
        await self.drain()
        return await self.request(
            "GET", f"/import-preparations/{result['preparation_id']}"
        )

    def draft(self, preparation: dict) -> dict:
        """Передаёт выбранные IDs изображений и проверенную ревизию без file_id."""
        return {
            "request_key": str(uuid4()),
            "preparation_id": preparation["preparation_id"],
            "expected_preparation_revision": preparation["revision"],
            "expected_observed_revision": preparation["observed_revision"],
            "values": preparation["values"],
        }

    async def test_full_woo_card_gallery_and_replay(self) -> None:
        """Сохраняет title/body/все фото, вычисляет наличие и возвращает тот же результат."""
        channel, pub = await self.imported()
        prepared = await self.prepare(pub)
        self.assertEqual(prepared["status"], "ready")
        self.assertEqual(prepared["values"]["titles"], {"uk": "Повна картка Woo"})
        self.assertEqual(
            prepared["values"]["descriptions"]["uk"],
            "<p>Опис <strong>товару</strong></p>",
        )
        self.assertEqual(len(prepared["images"]), 2)
        image = await self.client.get(prepared["images"][0]["preview_url"])
        self.assertEqual(
            image.status_code, 200, image.text if image.status_code != 200 else ""
        )
        self.assertEqual(image.content, PNG)
        body = self.draft(prepared)
        body["values"]["gallery"] = ["2", "1"]
        body["values"]["primary_image_id"] = "2"
        result = await self.request(
            "POST", f"/publications/{pub['publication_id']}/catalog-item", body, 201
        )
        item = (await self.catalog("GET", f"/{result['catalog_item_id']}?locale=uk"))[
            "item"
        ]
        self.assertEqual(item["status"], "draft")
        self.assertEqual(item["content"]["body"], body["values"]["descriptions"]["uk"])
        self.assertEqual(len(item["gallery"]["images"]), 2)
        self.assertEqual(item["gallery"]["images"][0]["alt"], "Друге фото")
        async with self.session() as session:
            await session.execute(
                update(ExternalPublicationModel)
                .where(ExternalPublicationModel.id == UUID(pub["publication_id"]))
                .values(observed_revision=pub["observed_revision"] + 1)
            )
        self.assertEqual(
            result,
            await self.request(
                "POST", f"/publications/{pub['publication_id']}/catalog-item", body, 201
            ),
        )
        self.assertEqual(await self.item_count(), 1)
        self.assertFalse(
            (await self.request("GET", f"/{channel['channel_id']}"))["is_enabled"]
        )

    async def test_prom_two_locales_and_common_files(self) -> None:
        """Переносит разные multilang тексты и общие Files в две локали Catalog."""
        _, pub = await self.imported("prom")
        preparation = await self.prepare(pub)
        self.assertEqual(set(preparation["values"]["titles"]), {"ru", "uk"})
        self.assertEqual(
            Decimal(preparation["values"]["sale_price"]), Decimal("100.50")
        )
        self.assertNotEqual(
            preparation["values"]["descriptions"]["ru"],
            preparation["values"]["descriptions"]["uk"],
        )
        result = await self.request(
            "POST",
            f"/publications/{pub['publication_id']}/catalog-item",
            self.draft(preparation),
            201,
        )
        uk = (await self.catalog("GET", f"/{result['catalog_item_id']}?locale=uk"))[
            "item"
        ]
        ru = (await self.catalog("GET", f"/{result['catalog_item_id']}?locale=ru"))[
            "item"
        ]
        self.assertEqual(uk["content"]["title"], "Назва з Prom")
        self.assertEqual(ru["content"]["title"], "Название с Prom")
        self.assertIn("Опис українською", uk["content"]["body"])
        self.assertIn("Описание по-русски", ru["content"]["body"])
        self.assertEqual(
            [i["file_id"] for i in uk["gallery"]["images"]],
            [i["file_id"] for i in ru["gallery"]["images"]],
        )
        self.assertEqual(len(self.downloader.calls), 2)

    async def test_image_retry_preserves_ready_file(self) -> None:
        """Повторяет только ошибочную фотографию; готовый файл не скачивается заново."""
        self.downloader.fail_second = True
        _, pub = await self.imported()
        preparation = await self.prepare(pub)
        self.assertEqual(preparation["images"][1]["error_code"], "image_network_error")
        await self.request(
            "POST",
            f"/publications/{pub['publication_id']}/catalog-item",
            self.draft(preparation),
            409,
        )
        self.downloader.fail_second = False
        await self.request(
            "POST",
            f"/import-preparations/{preparation['preparation_id']}/retry",
            {"expected_revision": preparation["revision"]},
        )
        await self.drain()
        ready = await self.request(
            "GET", f"/import-preparations/{preparation['preparation_id']}"
        )
        self.assertTrue(all(i["preview_url"] for i in ready["images"]))
        self.assertEqual(self.downloader.calls.count("https://images.example/1.png"), 1)

    async def test_cancel_cleanup_and_late_jobs(self) -> None:
        """Отмена запрещает создание и освобождает зарегистрированные временные файлы."""
        _, pub = await self.imported()
        preparation = await self.prepare(pub)
        await self.request(
            "POST",
            f"/import-preparations/{preparation['preparation_id']}/cancel",
            {"expected_revision": preparation["revision"]},
        )
        await self.drain()
        async with self.session() as session:
            statuses = list(await session.scalars(select(StoredFileModel.status)))
        self.assertEqual(statuses, ["trashed", "trashed"])
        await self.request(
            "POST",
            f"/publications/{pub['publication_id']}/catalog-item",
            self.draft(preparation),
            409,
        )

    async def test_invalid_sku_rolls_back_consumption_and_binding(self) -> None:
        """Неудачная валидация общего Catalog не расходует подготовку."""
        _, pub = await self.imported()
        preparation = await self.prepare(pub)
        await self.catalog(
            "POST", body={"sku": preparation["values"]["sku"]}, status=201
        )
        await self.request(
            "POST",
            f"/publications/{pub['publication_id']}/catalog-item",
            self.draft(preparation),
            422,
        )
        unchanged = await self.request(
            "GET", f"/import-preparations/{preparation['preparation_id']}"
        )
        self.assertEqual(unchanged["status"], "ready")
        self.assertEqual(unchanged["revision"], preparation["revision"])

    async def test_stale_connection_and_forged_gallery_rejected(self) -> None:
        """Не принимает чужие IDs фото, языки и настройку, изменённую после preview."""
        _, pub = await self.imported()
        preparation = await self.prepare(pub)
        forged = self.draft(preparation)
        forged["values"] = {
            **forged["values"],
            "gallery": ["foreign"],
            "primary_image_id": "foreign",
        }
        await self.request(
            "POST", f"/publications/{pub['publication_id']}/catalog-item", forged, 409
        )
        async with self.session() as session:
            await session.execute(
                update(ConnectionModel)
                .where(ConnectionModel.id == UUID(pub["connection_id"]))
                .values(generation=ConnectionModel.generation + 1)
            )
        await self.request(
            "POST",
            f"/publications/{pub['publication_id']}/catalog-item",
            self.draft(preparation),
            409,
        )
        self.assertEqual(await self.item_count(), 0)

    async def test_concurrent_full_creation_reuses_one_receipt(self) -> None:
        """Два подтверждения одной подготовки возвращают один товар и ту же галерею."""
        _, pub = await self.imported()
        preparation = await self.prepare(pub)
        body = self.draft(preparation)
        first, second = await asyncio.gather(
            self.request(
                "POST", f"/publications/{pub['publication_id']}/catalog-item", body, 201
            ),
            self.request(
                "POST", f"/publications/{pub['publication_id']}/catalog-item", body, 201
            ),
        )
        self.assertEqual(first, second)
        self.assertEqual(await self.item_count(), 1)

    async def test_expiry_cleanup_keeps_adopted_files_and_releases_excluded(
        self,
    ) -> None:
        """Очистка не затрагивает галерею созданного товара и освобождает исключённое фото."""
        _, pub = await self.imported()
        preparation = await self.prepare(pub)
        body = self.draft(preparation)
        body["values"] = {**body["values"], "gallery": ["1"], "primary_image_id": "1"}
        await self.request(
            "POST", f"/publications/{pub['publication_id']}/catalog-item", body, 201
        )
        identifier = UUID(preparation["preparation_id"])
        async with self.session() as session:
            await session.execute(
                update(PublicationImportModel)
                .where(PublicationImportModel.id == identifier)
                .values(
                    created_at=datetime.now(UTC) - timedelta(days=2),
                    expires_at=datetime.now(UTC) - timedelta(days=1),
                )
            )
            await build_publication_import_handlers(
                session, get_plugin_registry(), self.resolver
            ).cleanup.execute(CleanupPublicationImportCommand(self.tenant, identifier))
        async with self.session() as session:
            statuses = list(await session.scalars(select(StoredFileModel.status)))
        self.assertEqual(sorted(statuses), ["ready", "trashed"])
        self.assertEqual(
            await self.request(
                "POST", f"/publications/{pub['publication_id']}/catalog-item", body, 201
            ),
            await self.request(
                "POST", f"/publications/{pub['publication_id']}/catalog-item", body, 201
            ),
        )

    async def test_cleanup_preserves_file_used_by_another_catalog_item(self) -> None:
        """Публичный запрос Catalog защищает временное фото, прикреплённое другим сценарием."""
        _, pub = await self.imported()
        preparation = await self.prepare(pub)
        identifier = UUID(preparation["preparation_id"])
        async with self.session() as session:
            row = (
                await session.execute(
                    select(PublicationImportModel.media).where(
                        PublicationImportModel.id == identifier
                    )
                )
            ).scalar_one()
        file_id = row["2"]["file_id"]
        image_id = str(uuid4())
        await self.catalog(
            "POST",
            body={
                "galleries": {
                    "uk": {
                        "images": [{"id": image_id, "file_id": file_id, "position": 0}],
                        "primary_image_id": image_id,
                    }
                }
            },
            status=201,
        )
        await self.request(
            "POST",
            f"/import-preparations/{identifier}/cancel",
            {"expected_revision": preparation["revision"]},
        )
        await self.drain()
        async with self.session() as session:
            self.assertEqual(
                await session.scalar(
                    select(StoredFileModel.status).where(
                        StoredFileModel.id == UUID(file_id)
                    )
                ),
                "ready",
            )

    async def test_missing_worker_job_recovers_and_repeated_start_is_idempotent(
        self,
    ) -> None:
        """Потерянное задание отображается как восстановимое, GET не меняет SQL-состояние."""
        _, pub = await self.imported()
        identifier = str(uuid4())
        body = {
            "preparation_id": identifier,
            "expected_observed_revision": pub["observed_revision"],
        }
        first = await self.request(
            "POST",
            f"/publications/{pub['publication_id']}/import-preparations",
            body,
            202,
        )
        self.assertEqual(
            first,
            await self.request(
                "POST",
                f"/publications/{pub['publication_id']}/import-preparations",
                body,
                202,
            ),
        )
        async with self.sessions() as session:
            await session.execute(
                delete(ScheduledJobModel).where(
                    ScheduledJobModel.id == uuid5(UUID(identifier), "step:0")
                )
            )
            await session.commit()
        state = await self.request("GET", f"/import-preparations/{identifier}")
        self.assertEqual(state["error_code"], "import_worker_interrupted")
        async with self.session() as session:
            self.assertEqual(
                await session.scalar(
                    select(PublicationImportModel.status).where(
                        PublicationImportModel.id == UUID(identifier)
                    )
                ),
                "queued",
            )
        await self.request(
            "POST",
            f"/import-preparations/{identifier}/retry",
            {"expected_revision": state["revision"]},
        )
        await self.drain()
        self.assertEqual(
            (await self.request("GET", f"/import-preparations/{identifier}"))["status"],
            "ready",
        )

    async def test_preparation_and_private_images_are_tenant_and_actor_scoped(
        self,
    ) -> None:
        """Соседний пользователь или tenant не получают содержимое и файловый stream."""
        _, pub = await self.imported()
        preparation = await self.prepare(pub)
        body = self.draft(preparation)
        await self.request(
            "POST", f"/publications/{pub['publication_id']}/catalog-item", body, 201
        )
        old = self.app.state.test_context
        for actor, tenant in ((uuid4(), self.tenant), (self.actor, self.other)):
            self.app.state.test_context = replace(
                old, principal=Principal(str(actor), str(tenant), "test", ("member",))
            )
            await self.request(
                "GET",
                f"/import-preparations/{preparation['preparation_id']}",
                status=404,
            )
            response = await self.client.get(preparation["images"][0]["preview_url"])
            self.assertEqual(response.status_code, 404)
            await self.request(
                "POST",
                f"/publications/{pub['publication_id']}/catalog-item",
                body,
                409 if tenant == self.tenant else 404,
            )
        self.app.state.test_context = old

    async def test_read_failure_can_retry_without_blank_locale_fallback(self) -> None:
        """Отказ полного чтения сохраняется явно; повтор получает реальные тексты."""
        _, pub = await self.imported("prom")
        self.transport.denied = True
        preparation = await self.prepare(pub)
        self.assertEqual(preparation["status"], "error")
        self.assertIsNone(preparation["values"])
        self.transport.denied = False
        await self.request(
            "POST",
            f"/import-preparations/{preparation['preparation_id']}/retry",
            {"expected_revision": preparation["revision"]},
        )
        await self.drain()
        ready = await self.request(
            "GET", f"/import-preparations/{preparation['preparation_id']}"
        )
        self.assertEqual(ready["status"], "ready")
        self.assertEqual(set(ready["values"]["titles"]), {"ru", "uk"})
