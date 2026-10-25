"""HTTP и worker импорта на настоящем PostgreSQL с локальным файловым адаптером."""

import io
import os
import unittest
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from unittest.mock import patch
from uuid import UUID, uuid4
from sqlalchemy import insert, select, update, delete, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
import test.test_catalog_postgres as catalog_support_tests
from src.modules.catalog.presentation.catalog_import.jobs import CatalogImportJobHandler
from src.modules.catalog.presentation.catalog_import.runtime import CatalogImportRuntime
from src.modules.catalog.presentation.catalog_import.maintenance_job import (
    CatalogImportMaintenanceJobHandler,
)
from src.modules.catalog.infrastructure.catalog_import.repository import (
    SqlAlchemyCatalogImportRepository,
    SqlAlchemyImportRead,
)
from src.modules.catalog.infrastructure.catalog_import.download import (
    DownloadedImportFile,
)
from src.modules.catalog.domain.error import (
    InvalidCatalogValueError,
    CatalogNotFoundError,
)
from src.modules.shared.application.jobs.scheduled_job_deferred import (
    ScheduledJobDeferred,
)
from src.modules.shared.domain.jobs.scheduled_job import ScheduledJob
from src.modules.shared.infrastructure.jobs.scheduled_job_model import ScheduledJobModel
from src.modules.shared.infrastructure.persistence.unit_of_work.sqlalchemy import (
    UnitOfWork,
)
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_connection import (
    bind_tenant_schema,
)
from src.modules.files.infrastructure.persistence.models.storage_provider import (
    StorageProviderModel,
)
from src.modules.files.infrastructure.persistence.models.bucket import BucketModel
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


class MemoryStream:
    """Локальный объектный поток для проверки закрытия и неизменяемости байтов."""

    def __init__(self, data):
        self.data, self.closed = data, False

    async def __aiter__(self):
        for offset in range(0, len(self.data), 65536):
            yield self.data[offset : offset + 65536]

    async def aclose(self):
        self.closed = True


class MemoryStorage:
    """Файловый SDK заменён памятью; реестр Files остаётся настоящим SQL."""

    def __init__(self):
        self.data, self.writes = {}, 0

    def resolve(self, location):
        return self

    async def put(self, location, key, source, size, content_type):
        source.seek(0)
        data = source.read()
        self.data[location.tenant_id, key] = data
        self.writes += 1
        return len(data)

    async def open(self, location, key):
        return MemoryStream(self.data[location.tenant_id, key])


@unittest.skipUnless(
    os.environ.get("TEST_POSTGRES_URL"),
    "TEST_POSTGRES_URL requires a disposable database",
)
class CatalogImportPostgresTests(unittest.IsolatedAsyncioTestCase):
    """Проверяет полный процесс без обращения к поставщикам и рабочим данным."""

    asyncSetUpBase = catalog_support_tests.CatalogPostgresTests.asyncSetUp
    asyncTearDownBase = catalog_support_tests.CatalogPostgresTests.asyncTearDown

    async def asyncSetUp(self):
        await self.asyncSetUpBase()
        self.store = MemoryStorage()
        outer = self

        class Runtime(CatalogImportRuntime):
            @asynccontextmanager
            async def transaction(runtime):
                async with outer.engine.connect() as connection:
                    await bind_tenant_schema(
                        connection, runtime.tenant_id, outer.naming
                    )
                    async with UnitOfWork(
                        async_sessionmaker(connection, expire_on_commit=False)
                    ) as uow:
                        yield uow

        self.runtime_class = Runtime
        self.patches = [
            patch(
                "src.modules.catalog.presentation.catalog_import.jobs.CatalogImportRuntime",
                Runtime,
            ),
            patch(
                "src.modules.catalog.presentation.catalog_import.maintenance_job.CatalogImportRuntime",
                Runtime,
            ),
            patch(
                "src.modules.catalog.presentation.catalog_import.runtime.get_storage_resolver",
                return_value=self.store,
            ),
            patch(
                "src.modules.catalog.presentation.catalog_import.http.controller.create_catalog_import.get_storage_resolver",
                return_value=self.store,
            ),
        ]
        for item in self.patches:
            item.start()
        self.worker = CatalogImportJobHandler(self.sessions)
        self.csv = b"sku,title,regular_price,currency\nA,One,10,UAH\n"
        self.downloads = []

        async def download(url, limit, timeout):
            self.downloads.append(url)
            if url.endswith("/bad.png"):
                raise InvalidCatalogValueError("Image unavailable")
            data = b"\x89PNG\r\n\x1a\nimage" if url.endswith(".png") else self.csv
            return DownloadedImportFile(
                io.BytesIO(data), len(data), "application/octet-stream"
            )

        self.download_patch = patch(
            "src.modules.catalog.presentation.catalog_import.jobs.download_public_file",
            side_effect=download,
        )
        self.download_patch.start()
        image_download = patch(
            "src.modules.catalog.infrastructure.catalog_import.media.download_public_file",
            side_effect=download,
        )
        image_download.start()
        self.patches.append(image_download)
        for tenant in [self.tenant.uuid, self.other.uuid]:
            async with Runtime(self.sessions, tenant).transaction() as uow:
                provider, bucket = uuid4(), uuid4()
                await uow.session.execute(
                    insert(StorageProviderModel).values(
                        id=provider,
                        name="test",
                        kind="minio",
                        is_system=True,
                        config_ref="system_minio",
                    )
                )
                await uow.session.execute(
                    insert(BucketModel).values(
                        id=bucket,
                        provider_id=provider,
                        name=f"dnk-tenant-{tenant.hex}",
                        status="ready",
                    )
                )
                await uow.session.execute(
                    text(
                        "INSERT INTO public.ref_locales(code,language_code,name,active) VALUES ('uk','uk','Ukrainian',true) ON CONFLICT(code) DO UPDATE SET active=true"
                    )
                )

    async def asyncTearDown(self):
        self.download_patch.stop()
        for item in reversed(self.patches):
            item.stop()
        async with self.sessions() as session:
            await session.execute(
                delete(ScheduledJobModel).where(
                    ScheduledJobModel.tenant_id.in_([self.tenant.uuid, self.other.uuid])
                )
            )
            await session.commit()
        await self.asyncTearDownBase()

    async def create_import(self, data=None, key=None):
        if data is not None:
            self.csv = data
        response = await self.client.post(
            self.base + "/imports",
            json={"url": "https://example.com/source.csv", "default_locale": "ru"},
            headers={**self.headers, "Idempotency-Key": key or uuid4().hex},
        )
        self.assertEqual(response.status_code, 202, response.text)
        return response.json()["id"]

    async def get_import(self, identifier):
        response = await self.client.get(self.base + "/imports/" + identifier)
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    async def current_job(self, identifier):
        async with self.runtime_class(
            self.sessions, self.tenant.uuid
        ).transaction() as uow:
            entity = await SqlAlchemyCatalogImportRepository(uow.session).get(
                EntityIdVO(UUID(identifier))
            )
            job_id = entity.job_id.uuid
            now = datetime.now(UTC)
            await uow.session.execute(
                update(ScheduledJobModel)
                .where(ScheduledJobModel.id == job_id)
                .values(
                    status="running",
                    attempts=1,
                    lock_token="test-lease",
                    locked_until=now + timedelta(hours=1),
                )
            )
            row = (
                (
                    await uow.session.execute(
                        select(ScheduledJobModel.__table__).where(
                            ScheduledJobModel.id == job_id
                        )
                    )
                )
                .mappings()
                .one()
            )
            return ScheduledJob(
                **{name: row[name] for name in ScheduledJob.__dataclass_fields__}
            )

    async def execute_current(self, identifier):
        job = await self.current_job(identifier)
        await self.worker.handle(job)
        async with self.sessions() as session:
            await session.execute(
                update(ScheduledJobModel)
                .where(ScheduledJobModel.id == job.id)
                .values(status="done")
            )
            await session.commit()
        return job

    async def start_import(self, identifier):
        detail = await self.get_import(identifier)
        response = await self.client.post(
            f"{self.base}/imports/{identifier}/start",
            json={"version": detail["run"]["version"]},
            headers=self.headers,
        )
        self.assertEqual(response.status_code, 202, response.text)

    async def test_csv_http_preview_worker_results_idempotency_and_tenant_isolation(
        self,
    ):
        data = (
            "sku,title.ru,title.uk,regular_price,currency\n"
            'A,Один,Один,"507,7",UAH\nA,Повтор,Повтор,2,UAH\n'
            "BAD,Ошибка,Помилка,oops,UAH\n,Без SKU,Без SKU,0,UAH\n"
        ).encode("utf-8-sig")
        identifier = await self.create_import(data, "stable")
        self.assertEqual(await self.create_import(key="stable"), identifier)
        await self.execute_current(identifier)
        detail = await self.get_import(identifier)
        self.assertEqual(
            (detail["run"]["status"], detail["run"]["total"]), ("mapping", 4)
        )
        self.assertEqual(len(detail["analysis"]["samples"]), 4)
        await self.start_import(identifier)
        await self.start_import(identifier)
        job = await self.execute_current(identifier)
        await self.worker.handle(job)
        detail = await self.get_import(identifier)
        self.assertEqual(
            (
                detail["run"]["created"],
                detail["run"]["skipped"],
                detail["run"]["errors"],
            ),
            (2, 1, 1),
        )
        self.assertEqual(detail["run"]["processed"], 4)
        result = await self.client.get(
            f"{self.base}/imports/{identifier}/rows?outcome=errors"
        )
        self.assertEqual(result.json()["total"], 1)
        report = await self.client.get(f"{self.base}/imports/{identifier}/report.csv")
        self.assertEqual(report.status_code, 200)
        self.assertIn("BAD", report.text)
        self.assertEqual(len(self.downloads), 1)
        async with self.runtime_class(
            self.sessions, self.other.uuid
        ).transaction() as uow:
            with self.assertRaises(CatalogNotFoundError):
                await SqlAlchemyImportRead(uow.session).get(UUID(identifier))

    async def test_upload_same_bytes_snapshot_and_second_start_conflict(self):
        response = await self.client.post(
            self.base + "/imports",
            files={"file": ("products.csv", self.csv, "text/csv")},
            data={"default_locale": "ru"},
            headers={**self.headers, "Idempotency-Key": "upload"},
        )
        self.assertEqual(response.status_code, 202, response.text)
        identifier = response.json()["id"]
        await self.execute_current(identifier)
        await self.start_import(identifier)
        other = await self.create_import()
        await self.execute_current(other)
        detail = await self.get_import(other)
        conflict = await self.client.post(
            f"{self.base}/imports/{other}/start",
            json={"version": detail["run"]["version"]},
            headers=self.headers,
        )
        self.assertEqual(conflict.status_code, 409)
        await self.execute_current(identifier)
        self.assertEqual((await self.get_import(identifier))["run"]["created"], 1)
        self.assertEqual(len(self.downloads), 1)

    async def test_partial_update_preserves_other_translation_body_and_price(self):
        original = await self.client.post(
            self.base + "/items",
            json={
                "sku": "A",
                "price_specification": {"regular_price": "100", "currency": "UAH"},
                "translations": {
                    "ru": {
                        "expected_schema_version": 1,
                        "values": {"title": "Old", "body": "<p>Keep</p>"},
                    },
                    "uk": {"expected_schema_version": 1, "values": {"title": "Старе"}},
                },
            },
            headers=self.headers,
        )
        self.assertEqual(original.status_code, 201, original.text)
        item_id = original.json()["id"]
        identifier = await self.create_import(b"sku,title,sale_price\nA,New,85.50\n")
        await self.execute_current(identifier)
        detail = await self.get_import(identifier)
        configuration = detail["configuration"]
        configuration["mode"] = "update"
        changed = await self.client.put(
            f"{self.base}/imports/{identifier}/configuration",
            json=configuration,
            headers=self.headers,
        )
        self.assertEqual(changed.status_code, 202, changed.text)
        await self.execute_current(identifier)
        await self.start_import(identifier)
        await self.execute_current(identifier)
        self.assertEqual((await self.get_import(identifier))["run"]["updated"], 1)
        item = (await self.client.get(f"{self.base}/items/{item_id}?locale=ru")).json()[
            "item"
        ]
        self.assertEqual(item["content"]["title"], "New")
        self.assertEqual(item["content"]["body"], "<p>Keep</p>")
        self.assertEqual(
            Decimal(item["price_specification"]["regular_price"]), Decimal(100)
        )
        uk = (await self.client.get(f"{self.base}/items/{item_id}?locale=uk")).json()[
            "item"
        ]
        self.assertEqual(uk["content"]["title"], "Старе")

    async def test_lease_loss_rolls_back_and_retry_creates_once(self):
        identifier = await self.create_import()
        await self.execute_current(identifier)
        await self.start_import(identifier)
        job = await self.current_job(identifier)
        with patch.object(
            self.worker, "fence", side_effect=ScheduledJobDeferred("lost")
        ):
            with self.assertRaises(ScheduledJobDeferred):
                await self.worker.handle(job)
        self.assertEqual((await self.get_import(identifier))["run"]["processed"], 0)
        await self.worker.handle(job)
        await self.worker.handle(job)
        self.assertEqual((await self.get_import(identifier))["run"]["created"], 1)

    async def test_stop_before_processing_preserves_zero_results(self):
        identifier = await self.create_import()
        await self.execute_current(identifier)
        await self.start_import(identifier)
        response = await self.client.post(
            f"{self.base}/imports/{identifier}/cancel", headers=self.headers
        )
        self.assertEqual(response.status_code, 202)
        await self.execute_current(identifier)
        run = (await self.get_import(identifier))["run"]
        self.assertEqual((run["status"], run["processed"]), ("cancelled", 0))

    async def test_shared_images_partial_failure_preserves_existing_gallery(self):
        first = await self.create_import(
            b"sku,title.ru,title.uk,images\nA,First,First,https://example.com/old.png\n"
        )
        await self.execute_current(first)
        await self.start_import(first)
        job = await self.execute_current(first)
        rows = (await self.client.get(f"{self.base}/imports/{first}/rows")).json()[
            "items"
        ]
        item_id = rows[0]["item_id"]
        original_ru = (
            await self.client.get(f"{self.base}/items/{item_id}?locale=ru")
        ).json()["item"]["gallery"]
        original_uk = (
            await self.client.get(f"{self.base}/items/{item_id}?locale=uk")
        ).json()["item"]["gallery"]
        self.assertEqual(
            original_ru["images"][0]["file_id"], original_uk["images"][0]["file_id"]
        )
        self.assertNotEqual(
            original_ru["images"][0]["id"], original_uk["images"][0]["id"]
        )
        writes = self.store.writes
        await self.worker.handle(job)
        self.assertEqual(self.store.writes, writes)
        data = b'sku,title.ru,title.uk,images,primary_image\nA,Updated,Updated,"https://example.com/new.png, https://example.com/bad.png",2\nB,New,New,"https://example.com/new.png, https://example.com/bad.png",2\n'
        second = await self.create_import(data)
        await self.execute_current(second)
        detail = await self.get_import(second)
        config = detail["configuration"]
        config["mode"] = "upsert"
        response = await self.client.put(
            f"{self.base}/imports/{second}/configuration",
            json=config,
            headers=self.headers,
        )
        self.assertEqual(response.status_code, 202, response.text)
        await self.execute_current(second)
        await self.start_import(second)
        await self.execute_current(second)
        run = (await self.get_import(second))["run"]
        self.assertEqual((run["created"], run["updated"], run["errors"]), (1, 1, 0))
        self.assertGreater(run["warnings"], 0)
        current = (
            await self.client.get(f"{self.base}/items/{item_id}?locale=ru")
        ).json()["item"]
        self.assertEqual(current["gallery"], original_ru)
        self.assertEqual(current["content"]["title"], "Updated")
        rows = (await self.client.get(f"{self.base}/imports/{second}/rows")).json()[
            "items"
        ]
        new_id = next(r["item_id"] for r in rows if r["sku"] == "B")
        new_item = (
            await self.client.get(f"{self.base}/items/{new_id}?locale=uk")
        ).json()["item"]
        self.assertEqual(len(new_item["gallery"]["images"]), 1)
        self.assertEqual(self.downloads.count("https://example.com/new.png"), 1)
        self.assertEqual(self.downloads.count("https://example.com/bad.png"), 1)

    async def test_batches_resume_from_committed_cursor_and_stop_after_first(self):
        from src.config import dnk_config

        identifier = await self.create_import(b"sku,title\nA,One\nB,Two\nC,Three\n")
        await self.execute_current(identifier)
        await self.start_import(identifier)
        with patch.object(dnk_config.CATALOG_IMPORT, "batch_size", 1):
            first_job = await self.execute_current(identifier)
        self.assertEqual((await self.get_import(identifier))["run"]["processed"], 1)
        await self.worker.handle(first_job)
        self.assertEqual((await self.get_import(identifier))["run"]["processed"], 1)
        await self.client.post(
            f"{self.base}/imports/{identifier}/cancel", headers=self.headers
        )
        await self.execute_current(identifier)
        run = (await self.get_import(identifier))["run"]
        self.assertEqual(
            (run["status"], run["processed"], run["created"]), ("cancelled", 1, 1)
        )

    async def test_source_retention_and_results_cleanup_do_not_delete_product(self):
        from src.modules.catalog.application.catalog_import.command.maintain_catalog_imports.command import (
            MaintainCatalogImportsCommand,
        )
        from src.modules.catalog.application.catalog_import.command.maintain_catalog_imports.handler import (
            MaintainCatalogImportsHandler,
        )
        from src.modules.catalog.infrastructure.catalog_import.maintenance import (
            SqlAlchemyImportMaintenance,
        )
        from src.modules.catalog.presentation.catalog_import.assembly import (
            build_import_queue,
        )
        from src.modules.files.infrastructure.persistence.models.stored_file import (
            StoredFileModel,
        )

        identifier = await self.create_import()
        await self.execute_current(identifier)
        await self.start_import(identifier)
        await self.execute_current(identifier)
        async with self.runtime_class(
            self.sessions, self.tenant.uuid
        ).transaction() as uow:
            entity = await SqlAlchemyCatalogImportRepository(uow.session).get(
                EntityIdVO(UUID(identifier))
            )
            source_id = entity.source_file_id.uuid
            handler = MaintainCatalogImportsHandler(
                SqlAlchemyCatalogImportRepository(uow.session),
                SqlAlchemyImportMaintenance(uow.session, self.tenant.uuid),
                build_import_queue(uow.session, self.tenant.uuid),
                24,
                7,
                30,
            )
            await handler.execute(
                MaintainCatalogImportsCommand(
                    UUID(identifier), datetime.now(UTC) + timedelta(days=8)
                )
            )
            self.assertEqual(
                await uow.session.scalar(
                    select(StoredFileModel.status).where(
                        StoredFileModel.id == source_id
                    )
                ),
                "trashed",
            )
        self.assertEqual((await self.get_import(identifier))["analysis"]["samples"], [])
        async with self.runtime_class(
            self.sessions, self.tenant.uuid
        ).transaction() as uow:
            handler = MaintainCatalogImportsHandler(
                SqlAlchemyCatalogImportRepository(uow.session),
                SqlAlchemyImportMaintenance(uow.session, self.tenant.uuid),
                build_import_queue(uow.session, self.tenant.uuid),
                24,
                7,
                30,
            )
            result = await handler.execute(
                MaintainCatalogImportsCommand(
                    UUID(identifier), datetime.now(UTC) + timedelta(days=31)
                )
            )
            self.assertEqual(result.deleted, 1)
        self.assertEqual(
            (await self.client.get(f"{self.base}/imports/{identifier}")).status_code,
            404,
        )
        self.assertEqual(
            (await self.client.get(self.base + "/items?locale=ru")).json()["total"], 1
        )

    async def test_upload_limit_csrf_and_validation(self):
        from src.config import dnk_config

        with patch.object(dnk_config.CATALOG_IMPORT, "source_max_bytes", 10):
            response = await self.client.post(
                self.base + "/imports",
                files={"file": ("large.csv", b"x" * 100, "text/csv")},
                headers={**self.headers, "Idempotency-Key": "large"},
            )
        self.assertEqual(response.status_code, 413)
        self.assertEqual(self.store.writes, 0)
        response = await self.client.post(
            self.base + "/imports",
            json={"url": "https://example.com/source.csv"},
            headers={"Idempotency-Key": "no-csrf"},
        )
        self.assertEqual(response.status_code, 403)
        response = await self.client.post(
            self.base + "/imports",
            json={"url": "http://127.0.0.1/source.csv"},
            headers={**self.headers, "Idempotency-Key": "private"},
        )
        self.assertEqual(response.status_code, 422)

    async def test_concurrent_sku_edit_never_updates_the_wrong_item(self):
        from src.modules.catalog.infrastructure.catalog_import.repository import (
            SqlAlchemyImportRows,
        )

        original = await self.client.post(
            self.base + "/items",
            json={
                "sku": "A",
                "translations": {
                    "ru": {"expected_schema_version": 1, "values": {"title": "Keep"}}
                },
            },
            headers=self.headers,
        )
        self.assertEqual(original.status_code, 201, original.text)
        item_id = original.json()["id"]
        identifier = await self.create_import(b"sku,title\nA,Must not replace\n")
        await self.execute_current(identifier)
        detail = await self.get_import(identifier)
        configuration = detail["configuration"]
        configuration["mode"] = "update"
        await self.client.put(
            f"{self.base}/imports/{identifier}/configuration",
            json=configuration,
            headers=self.headers,
        )
        await self.execute_current(identifier)
        await self.start_import(identifier)
        find_item = SqlAlchemyImportRows.find_item

        async def edit_after_lookup(repository, sku):
            found = await find_item(repository, sku)
            response = await self.client.patch(
                f"{self.base}/items/{item_id}", json={"sku": "B"}, headers=self.headers
            )
            self.assertEqual(response.status_code, 200, response.text)
            return found

        with patch.object(SqlAlchemyImportRows, "find_item", edit_after_lookup):
            await self.execute_current(identifier)
        run = (await self.get_import(identifier))["run"]
        self.assertEqual((run["errors"], run["updated"]), (1, 0))
        item = (await self.client.get(f"{self.base}/items/{item_id}?locale=ru")).json()[
            "item"
        ]
        self.assertEqual((item["sku"], item["content"]["title"]), ("B", "Keep"))
