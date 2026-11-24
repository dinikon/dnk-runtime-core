"""Сквозная проверка экспорта из jobs worker в Files и публичный tenant HTTP."""

import asyncio
from copy import deepcopy
import csv
from datetime import UTC, datetime
from decimal import Decimal
from io import StringIO
import os
import unittest
from unittest.mock import patch
from urllib.parse import urlsplit
from uuid import uuid4
from xml.etree import ElementTree

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, select, update

from src.modules.feed_builder.application.export_state.job_types import (
    RECONCILE_JOB_TYPE,
    REFRESH_JOB_TYPE,
    RETIRE_FILE_JOB_TYPE,
)
from src.modules.feed_builder.application.feed.schema_definition import decode_schema
from src.modules.feed_builder.application.feed.schema_document import field_document, schema_document
from src.modules.feed_builder.domain.feed.enum.catalog_source_path import (
    CatalogSourcePath,
)
from src.modules.feed_builder.domain.feed.enum.locale_fallback_mode import (
    LocaleFallbackMode,
)
from src.modules.feed_builder.domain.feed.enum.source_provider import SourceProvider
from src.modules.feed_builder.domain.feed.value_object.locale_code import LocaleCodeVO
from src.modules.feed_builder.domain.feed.value_object.locale_fallback_policy import (
    LocaleFallbackPolicyVO,
)
from src.modules.feed_builder.domain.feed.value_object.manual_value_definition import (
    ManualValueDefinitionVO,
)
from src.modules.feed_builder.domain.feed.value_object.source_reference import (
    SourceReferenceVO,
)
from src.modules.feed_builder.domain.feed.value_object.source_value_definition import (
    SourceValueDefinitionVO,
)
from src.modules.feed_builder.domain.feed.value_object.string_field_type import (
    StringFieldTypeVO,
)
from src.modules.feed_builder.domain.feed.value_object.text_constraints import (
    TextConstraintsVO,
)
from src.modules.feed_builder.domain.feed.value_object.text_field_type import (
    TextFieldTypeVO,
)
from src.modules.feed_builder.infrastructure.persistence.models.export_state import (
    FeedExportStateModel,
)
from src.modules.feed_builder.presentation.export_state.jobs import (
    FeedExportJobHandler,
    ReconcileFeedExportJobHandler,
    RetireFeedExportFileJobHandler,
)
from src.modules.feed_builder.presentation.export_state.router import (
    public_router,
    router,
)
from src.modules.files.application.bucket.command.provision_system_bucket.command import (
    ProvisionSystemBucketCommand,
)
from src.modules.files.application.stored_file.command.trash_file.command import (
    TrashFileCommand,
)
from src.modules.files.application.stored_file.query.list_files.query import ListFilesQuery
from src.modules.files.application.storage_provider.command.register_system_storage.command import (
    RegisterSystemStorageCommand,
)
from src.modules.files.domain.stored_file.error import FileInUseError
from src.modules.files.infrastructure.assembly import build_files_handlers
from src.modules.files.infrastructure.persistence.models.stored_file import (
    StoredFileModel,
)
from src.modules.files.presentation.jobs.purge_file import FilesPurgeJobHandler
from src.modules.shared.application.jobs.in_memory_scheduled_job_dispatcher import (
    InMemoryScheduledJobDispatcher,
)
from src.modules.shared.application.jobs.schedule_scheduled_job_command import (
    ScheduleScheduledJobCommand,
)
from src.modules.shared.application.jobs.schedule_scheduled_job_use_case import (
    ScheduleScheduledJobUseCase,
)
from src.modules.shared.infrastructure.jobs.scheduled_job_model import ScheduledJobModel
from src.modules.shared.infrastructure.jobs.sqlalchemy_scheduled_job_repository import (
    SqlAlchemyScheduledJobRepository,
)
from src.modules.shared.infrastructure.jobs.worker import ScheduledJobWorker
from src.modules.shared.infrastructure.persistence.tenant_cleanup import (
    delete_shared_tenant_records,
)
from src.modules.shared.infrastructure.time import UtcClock
from src.modules.tenancy.infrastructure.persistence.tenant import TenantModel
from src.modules.tenancy.infrastructure.persistence.tenant_domain import (
    TenantDomainModel,
)
from src.modules.tenancy.presentation.tenant.http.tenant_gate import (
    TenantAdmissionMiddleware,
)
from test import test_feed_builder_publications_postgres as fixture
from test import test_feed_builder_crud_postgres as crud_fixture
from test.test_feed_builder_domain import money_field, text_field


@unittest.skipUnless(
    os.environ.get("TEST_POSTGRES_URL") and os.environ.get("TEST_MINIO_ENDPOINT"),
    "Requires disposable PostgreSQL and MinIO",
)
class FeedExportPostgresTests(unittest.IsolatedAsyncioTestCase):
    """Проверяет очередь, переключение файла, отчёт, ротацию и tenant isolation."""

    refresh_csrf = fixture.FeedPublicationsPostgresTests.refresh_csrf
    scoped_session = fixture.FeedPublicationsPostgresTests.scoped_session
    create = fixture.FeedPublicationsPostgresTests.create
    item = fixture.FeedPublicationsPostgresTests.item
    add = fixture.FeedPublicationsPostgresTests.add

    async def asyncSetUp(self) -> None:
        """Готовит два tenant-хоста с реальным middleware и Storage."""
        await fixture.FeedPublicationsPostgresTests.asyncSetUp(self)
        self.app.state.clock = UtcClock()
        self.app.include_router(router, prefix="/api/console")
        self.tenant_host = f"{self.tenant.uuid.hex}.tenant.example"
        self.other_host = f"{self.other.uuid.hex}.tenant.example"
        self.origin = self.origin.replace("tenant.example", self.tenant_host)
        self.client.base_url = self.origin
        await self.refresh_csrf()
        async with self.sessions.begin() as session:
            for tenant, host in (
                (self.tenant, self.tenant_host),
                (self.other, self.other_host),
            ):
                await session.execute(
                    TenantModel.__table__.insert().values(
                        id=tenant.uuid,
                        name=f"feed-export-{tenant.uuid}",
                        external_id=str(tenant.uuid),
                        status="active",
                    )
                )
                await session.execute(
                    TenantDomainModel.__table__.insert().values(
                        tenant_id=tenant.uuid,
                        host=host,
                        service_type="console",
                        kind="custom",
                        status="active",
                    )
                )
        async with self.scoped_session() as session:
            registration = await build_files_handlers(session).register.execute(
                RegisterSystemStorageCommand(self.tenant.uuid)
            )
        async with self.scoped_session() as session:
            await build_files_handlers(session).provision.execute(
                ProvisionSystemBucketCommand(self.tenant.uuid, registration.bucket_id)
            )
        public_app = FastAPI()
        public_app.state.db = self.sessions
        public_app.include_router(public_router)
        public_app.add_middleware(TenantAdmissionMiddleware)
        self.public = AsyncClient(
            transport=ASGITransport(app=public_app),
            base_url=f"https://{self.tenant_host}",
        )
        self.root = f"{self.base}/{self.feed['id']}"
        self.worker = ScheduledJobWorker(
            session_factory=self.sessions,
            dispatcher=InMemoryScheduledJobDispatcher(
                {
                    REFRESH_JOB_TYPE: FeedExportJobHandler(self.sessions, self.naming),
                    RECONCILE_JOB_TYPE: ReconcileFeedExportJobHandler(
                        self.sessions, self.naming
                    ),
                    RETIRE_FILE_JOB_TYPE: RetireFeedExportFileJobHandler(
                        self.sessions, self.naming
                    ),
                    "files.purge": FilesPurgeJobHandler(self.sessions),
                }
            ),
            process_limit=10,
            recover_limit=10,
            lock_ttl_seconds=30,
            lock_heartbeat_seconds=5,
            retry_base_seconds=1,
            max_attempts=2,
            poll_interval_seconds=0.1,
            recover_interval_seconds=1,
            heartbeat_path=None,
        )

    async def asyncTearDown(self) -> None:
        """Закрывает HTTP-клиенты и очищает временные схемы."""
        await self.public.aclose()
        async with self.sessions.begin() as session:
            for tenant in (self.tenant, self.other):
                await delete_shared_tenant_records(session, tenant.uuid)
                await session.execute(
                    delete(TenantDomainModel).where(
                        TenantDomainModel.tenant_id == tenant.uuid
                    )
                )
                await session.execute(
                    delete(TenantModel).where(TenantModel.id == tenant.uuid)
                )
        await fixture.FeedPublicationsPostgresTests.asyncTearDown(self)

    async def export_state(self) -> dict:
        """Читает единственное актуальное состояние через Console API."""
        response = await self.client.get(f"{self.root}/export")
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    async def save_schema(self, version: int, fields: list[dict]) -> int:
        """Сохраняет рабочую схему перед постановкой."""
        saved = await self.client.put(
            f"{self.root}/schema/draft",
            headers=self.headers,
            json={
                "expected_version": version,
                "definition": {
                    "schema_format_version": 1,
                    "root": {
                        "key": "publication",
                        "kind": "object",
                        "fields": fields,
                    },
                },
            },
        )
        self.assertEqual(saved.status_code, 200, saved.text)
        return saved.json()["version"]

    async def enqueue(self, version: int) -> None:
        """Вызывает реальный refresh c CSRF и проверяет постановку."""
        refresh = await self.client.post(
            f"{self.root}/export/refresh",
            headers=self.headers,
            json={"expected_version": version},
        )
        self.assertEqual(refresh.status_code, 202, refresh.text)
        self.assertEqual(refresh.json()["status"], "PENDING")

    async def save_validation_policy(self, version: int, policy: str) -> int:
        """Сохраняет режим проверки с текущими настройками формата."""
        current = await self.client.get(self.root)
        self.assertEqual(current.status_code, 200, current.text)
        settings = current.json()["export_settings"] | {"validation_policy": policy}
        updated = await self.client.patch(
            self.root,
            headers=self.headers,
            json={"expected_version": version, "export_settings": settings},
        )
        self.assertEqual(updated.status_code, 200, updated.text)
        self.assertEqual(updated.json()["export_settings"]["validation_policy"], policy)
        return updated.json()["version"]

    async def make_due(self, kind: str) -> None:
        """Ускоряет ожидание только задач этого тестового tenant."""
        async with self.sessions.begin() as session:
            await session.execute(
                update(ScheduledJobModel)
                .where(
                    ScheduledJobModel.tenant_id == self.tenant.uuid,
                    ScheduledJobModel.job_type == kind,
                    ScheduledJobModel.status == "scheduled",
                )
                .values(run_at=datetime.now(UTC))
            )

    async def test_current_file_report_rotation_and_cleanup(self) -> None:
        """Строит полный CSV, сохраняет ссылку и защищает последнюю успешную выдачу."""
        field = field_document(
            text_field(
                "item_sku",
                type_definition=StringFieldTypeVO(
                    SourceValueDefinitionVO(
                        SourceReferenceVO(SourceProvider.CATALOG, CatalogSourcePath.SKU)
                    ),
                    constraints=TextConstraintsVO(required=True),
                ),
            )
        )
        await crud_fixture.FeedCrudPostgresTests.seed_schema_locales(self)
        title = field_document(
            text_field(
                "title",
                type_definition=StringFieldTypeVO(
                    SourceValueDefinitionVO(
                        SourceReferenceVO(
                            SourceProvider.CATALOG, CatalogSourcePath.TITLE
                        )
                    ),
                    locale=LocaleCodeVO("uk"),
                    fallback_policy=LocaleFallbackPolicyVO(
                        LocaleFallbackMode.LOCALE_CHAIN, (LocaleCodeVO("ru"),)
                    ),
                ),
            )
        )
        version = await self.save_schema(1, [field, title])
        refs = [{"catalog_item_id": await self.item()} for _ in range(103)]
        copied_title = await self.client.patch(
            f"{self.catalog}/{refs[0]['catalog_item_id']}?locale=ru",
            headers=self.headers,
            json={
                "content": {
                    "expected_schema_version": 1,
                    "values": {"title": "Резервный заголовок"},
                }
            },
        )
        self.assertEqual(copied_title.status_code, 200, copied_title.text)
        added = await self.add(refs[:100], expected=version)
        await self.add(refs[100:], expected=version)
        self.assertIsNone((await self.export_state())["active"])
        await asyncio.gather(self.enqueue(version), self.enqueue(version))
        async with self.sessions() as session:
            jobs = (
                await session.scalars(
                    select(ScheduledJobModel.id).where(
                        ScheduledJobModel.tenant_id == self.tenant.uuid,
                        ScheduledJobModel.job_type == REFRESH_JOB_TYPE,
                    )
                )
            ).all()
        self.assertEqual(len(jobs), 1)
        await self.worker.process_once()

        first = await self.export_state()
        self.assertIsNone(first["task"])
        self.assertEqual(first["report"]["outcome"], "PUBLISHED")
        self.assertEqual(first["report"]["valid_items"], 102)
        self.assertEqual(first["report"]["warning_items"], 1)
        warnings = await self.client.get(f"{self.root}/export/issues?severity=WARNING")
        self.assertEqual(warnings.status_code, 200, warnings.text)
        self.assertEqual(warnings.json()["items"][0]["code"], "LOCALE_FALLBACK")
        path = urlsplit(first["active"]["url"]).path
        result = await self.public.get(path)
        self.assertEqual(result.status_code, 200, result.text)
        rows = list(csv.reader(StringIO(result.text), delimiter=";"))
        self.assertEqual(len(rows), 103)
        self.assertEqual(len({row[0] for row in rows}), 103)
        self.assertEqual(
            result.headers["content-disposition"], 'attachment; filename="feed.csv"'
        )
        etag = result.headers["etag"]
        self.assertEqual(
            (await self.public.get(path, headers={"If-None-Match": etag})).status_code,
            304,
        )
        self.assertEqual(
            (await self.public.get(f"https://{self.other_host}" + path)).status_code,
            404,
        )
        self.assertEqual(
            (await self.public.get("https://unregistered.example" + path)).status_code,
            404,
        )
        async with self.scoped_session() as session:
            original_file = await session.scalar(
                select(FeedExportStateModel.active_file_id)
            )
            record = await session.get(StoredFileModel, original_file)
            self.assertEqual(record.status, "ready")
            files = build_files_handlers(session)
            listing = await files.files.execute(ListFilesQuery(self.tenant.uuid))
            self.assertEqual(
                [(item.file_id, item.name) for item in listing.items],
                [(original_file, "feed.csv")],
            )
            with self.assertRaises(FileInUseError):
                await files.trash_file.execute(
                    TrashFileCommand(self.tenant.uuid, original_file, self.actor)
                )

        publication_id = added["items"][0]["id"]
        override = await self.client.put(
            f"/api/console/feed-builder/publications/{publication_id}/overrides/{field['id']}",
            headers=self.headers,
            json={
                "value": "CURRENT-SKU",
                "expected_version": 1,
                "expected_feed_version": first["feed_version"],
            },
        )
        self.assertEqual(override.status_code, 200, override.text)
        await self.enqueue(first["feed_version"])
        with patch.object(
            SqlAlchemyScheduledJobRepository,
            "owns_current_lease",
            side_effect=[True, False],
        ):
            await self.worker.process_once()
        deferred = await self.export_state()
        self.assertEqual(deferred["task"]["status"], "RUNNING")
        self.assertEqual(deferred["active"], first["active"])
        self.assertEqual(deferred["report"], first["report"])
        async with self.scoped_session() as session:
            listing = await build_files_handlers(session).files.execute(
                ListFilesQuery(self.tenant.uuid)
            )
            self.assertEqual(listing.total, 1)

        await self.make_due(REFRESH_JOB_TYPE)
        await self.worker.process_once()
        second = await self.export_state()
        self.assertEqual(second["report"]["as_of"], deferred["task"]["started_at"])
        self.assertEqual(second["active"]["url"], first["active"]["url"])
        updated = await self.public.get(path, headers={"If-None-Match": etag})
        self.assertEqual(updated.status_code, 200, updated.text)
        self.assertIn("CURRENT-SKU", updated.text)
        await self.make_due(RETIRE_FILE_JOB_TYPE)
        await self.worker.process_once()
        await self.worker.process_once()
        async with self.scoped_session() as session:
            self.assertIsNone(await session.get(StoredFileModel, original_file))
            self.assertIsNotNone(
                await session.scalar(select(FeedExportStateModel.active_file_id))
            )

        await self.enqueue(second["feed_version"])
        field["type_definition"]["constraints"]["max_length"] = 1
        version = await self.save_schema(second["feed_version"], [field, title])
        await self.worker.process_once()
        stale = await self.export_state()
        self.assertEqual(stale["report"]["reason_code"], "FEED_CHANGED")
        self.assertEqual(stale["active"], second["active"])
        await self.enqueue(version)
        await self.worker.process_once()
        rejected = await self.export_state()
        self.assertEqual(rejected["report"]["outcome"], "REJECTED")
        self.assertEqual(rejected["report"]["rejected_items"], 103)
        self.assertEqual(rejected["active"], second["active"])
        issues = await self.client.get(
            f"{self.root}/export/issues?severity=ERROR&limit=5"
        )
        self.assertEqual(issues.status_code, 200, issues.text)
        self.assertEqual((issues.json()["total"], len(issues.json()["items"])), (103, 5))
        empty_page = await self.client.get(
            f"{self.root}/export/issues?severity=ERROR&offset=103"
        )
        self.assertEqual(empty_page.json(), {"items": [], "total": 103})
        self.assertEqual((await self.public.get(path)).content, updated.content)

        rotated = await self.client.post(
            f"{self.root}/public-link/rotate",
            headers=self.headers,
            json={"expected_version": version},
        )
        self.assertEqual(rotated.status_code, 200, rotated.text)
        replacement = urlsplit(rotated.json()["url"]).path
        self.assertNotEqual(path, replacement)
        self.assertEqual(
            (
                await self.public.get(
                    path, headers={"If-None-Match": updated.headers["etag"]}
                )
            ).status_code,
            404,
        )
        self.assertEqual((await self.public.get(replacement)).content, updated.content)

        await self.enqueue(rotated.json()["feed_version"])
        async with self.scoped_session() as session:
            job_id = await session.scalar(select(FeedExportStateModel.job_id))
        async with self.sessions.begin() as session:
            await session.execute(
                update(ScheduledJobModel)
                .where(
                    ScheduledJobModel.tenant_id == self.tenant.uuid,
                    ScheduledJobModel.id == job_id,
                )
                .values(status="failed")
            )
            await session.execute(
                update(ScheduledJobModel)
                .where(
                    ScheduledJobModel.tenant_id == self.tenant.uuid,
                    ScheduledJobModel.job_type == RECONCILE_JOB_TYPE,
                    ScheduledJobModel.payload["job_id"].astext == str(job_id),
                )
                .values(run_at=datetime.now(UTC))
            )
        await self.worker.process_once()
        failed = await self.export_state()
        self.assertEqual(failed["report"]["outcome"], "FAILED")
        self.assertIsNone(failed["task"])
        self.assertEqual((await self.public.get(replacement)).content, updated.content)

        archived = await self.client.delete(
            self.root,
            headers=self.headers,
            params={"expected_version": rotated.json()["feed_version"]},
        )
        self.assertEqual(archived.status_code, 204, archived.text)
        self.assertEqual((await self.public.get(replacement)).status_code, 404)

    async def test_xml_switch_serialization_and_public_link(self) -> None:
        """Публикует XML по действующей схеме, сохраняя CSV до успеха STRICT."""
        title = field_document(
            text_field(
                "title", type_definition=TextFieldTypeVO(ManualValueDefinitionVO())
            )
        )
        title["export"]["xml_placement"] = "ATTRIBUTE"
        optional = field_document(text_field("optional"))
        optional["export"]["xml_placement"] = "ATTRIBUTE"
        price = field_document(money_field())
        plain_price = field_document(money_field())
        plain_price["key"] = "plain_price"
        plain_price["export"]["name"] = "plain_price"
        plain_price["type_definition"]["currency"] = None
        attr_price = field_document(money_field())
        attr_price["key"] = "attr_price"
        attr_price["export"].update(name="attr_price", xml_placement="ATTRIBUTE")
        fields = [title, optional, price, plain_price, attr_price]
        version = await self.save_schema(1, fields)
        added = await self.add(
            [{"catalog_item_id": await self.item()}], expected=version
        )
        publication_id = added["items"][0]["id"]
        override_url = f"/api/console/feed-builder/publications/{publication_id}/overrides/{title['id']}"
        publication_version = 1

        async def override_title(value: str, feed_version: int) -> None:
            """Сохраняет значение поля по актуальным версиям агрегатов."""
            nonlocal publication_version
            response = await self.client.put(
                override_url,
                headers=self.headers,
                json={
                    "value": value,
                    "expected_version": publication_version,
                    "expected_feed_version": feed_version,
                },
            )
            self.assertEqual(response.status_code, 200, response.text)
            publication_version = response.json()["publication_version"]

        await override_title("Исходный CSV", version)
        preview = await self.client.post(
            f"{self.root}/preview",
            headers=self.headers,
            json={"expected_version": version},
        )
        self.assertEqual(preview.status_code, 200, preview.text)
        self.assertTrue(
            all(not col["xml_attribute"] for col in preview.json()["columns"])
        )
        await self.enqueue(version)
        await self.worker.process_once()
        csv_state = await self.export_state()
        csv_path = urlsplit(csv_state["active"]["url"]).path
        csv_file = await self.public.get(csv_path)
        self.assertEqual(csv_file.status_code, 200, csv_file.text)
        self.assertIn("Исходный CSV", csv_file.text)
        csv_row = next(csv.reader(StringIO(csv_file.text), delimiter=";"))
        self.assertEqual(csv_row[0], "Исходный CSV")
        self.assertEqual(csv_row[-1], csv_row[2])
        xml_path = f"{csv_path.removesuffix('.csv')}.xml"
        options = {"format": "xml", "root_name": "offers", "item_name": "offer"}
        for root, status in (("invalid root", 422), ("offers", 200)):
            changed = await self.client.patch(
                self.root,
                headers=self.headers,
                json={
                    "expected_version": csv_state["feed_version"],
                    "export_settings": {
                        "format_settings": options | {"root_name": root}
                    },
                },
            )
            self.assertEqual(changed.status_code, status, changed.text)
        version = changed.json()["version"]
        configured = await self.export_state()
        self.assertTrue(configured["can_refresh"])
        self.assertEqual(configured["active"], csv_state["active"])

        await override_title("Недопустимый\x01символ", version)
        await self.enqueue(version)
        await self.worker.process_once()
        rejected = await self.export_state()
        self.assertEqual(rejected["report"]["outcome"], "REJECTED")
        self.assertEqual(rejected["report"]["rejected_items"], 1)
        self.assertEqual(rejected["active"], csv_state["active"])
        issues = await self.client.get(f"{self.root}/export/issues")
        issue = issues.json()["items"][0]
        self.assertEqual(
            (issue["code"], issue["field_id"]), ("XML_INVALID_CHARACTER", title["id"])
        )
        self.assertEqual((await self.public.get(csv_path)).content, csv_file.content)
        self.assertEqual((await self.public.get(xml_path)).status_code, 404)

        special_title = '=Київ & <ліки> "назва"\r\n\t🧪'
        await override_title(special_title, version)
        preview = await self.client.post(
            f"{self.root}/preview",
            headers=self.headers,
            json={"expected_version": version},
        )
        self.assertEqual(preview.status_code, 200, preview.text)
        self.assertEqual(
            [col["name"] for col in preview.json()["columns"] if col["xml_attribute"]],
            ["title", "optional", "attr_price"],
        )
        preview_values = preview.json()["rows"][0]["values"]
        self.assertEqual(preview_values[0], special_title)
        self.assertIsNone(preview_values[1])
        await self.enqueue(version)
        await self.worker.process_once()
        published = await self.export_state()
        self.assertEqual(published["report"]["outcome"], "PUBLISHED")
        self.assertEqual(published["active"]["format"], "xml")
        self.assertEqual(urlsplit(published["active"]["url"]).path, xml_path)
        public_xml = await self.public.get(xml_path)
        self.assertEqual(public_xml.status_code, 200, public_xml.text)
        self.assertEqual(public_xml.headers["content-type"], "application/xml")
        self.assertEqual(
            public_xml.headers["content-disposition"], 'inline; filename="feed.xml"'
        )
        self.assertEqual(
            int(public_xml.headers["content-length"]), len(public_xml.content)
        )
        self.assertIn(b"&amp; &lt;", public_xml.content)
        root = ElementTree.fromstring(public_xml.content)
        self.assertEqual(root.tag, "offers")
        self.assertEqual([row.tag for row in root], ["offer"])
        self.assertEqual(
            root[0].attrib, {"title": special_title, "attr_price": preview_values[-1]}
        )
        self.assertEqual(
            [field.tag for field in root[0]], ["partner_amount", "plain_price"]
        )
        self.assertEqual(root[0][0].attrib, {"currency": "UAH"})
        self.assertEqual(root[0][1].attrib, {})
        self.assertEqual(Decimal(root[0][0].text), Decimal("1000"))
        self.assertEqual(root[0][0].text, root[0][1].text)
        self.assertEqual(root[0].attrib["attr_price"], root[0][0].text)
        etag = public_xml.headers["etag"]
        self.assertEqual((await self.public.get(csv_path)).status_code, 404)
        self.assertEqual(
            (
                await self.public.get(xml_path, headers={"If-None-Match": etag})
            ).status_code,
            304,
        )
        self.assertEqual(
            (await self.public.get(f"https://{self.other_host}{xml_path}")).status_code,
            404,
        )
        async with self.scoped_session() as session:
            listing = await build_files_handlers(session).files.execute(
                ListFilesQuery(self.tenant.uuid)
            )
            self.assertIn(
                ("feed.xml", "application/xml"),
                [(file.name, file.content_type) for file in listing.items],
            )

        title["export"]["xml_placement"] = "ELEMENT"
        version = await self.save_schema(published["feed_version"], fields)
        await override_title("Обновлённый XML", version)
        await self.enqueue(version)
        await self.worker.process_once()
        updated = await self.export_state()
        self.assertEqual(updated["active"]["url"], published["active"]["url"])
        result = await self.public.get(xml_path, headers={"If-None-Match": etag})
        self.assertEqual(result.status_code, 200, result.text)
        offer = ElementTree.fromstring(result.content)[0]
        self.assertNotIn("title", offer.attrib)
        self.assertEqual(offer.findtext("title"), "Обновлённый XML")
        rotated = await self.client.post(
            f"{self.root}/public-link/rotate",
            headers=self.headers,
            json={"expected_version": updated["feed_version"]},
        )
        self.assertEqual(rotated.status_code, 200, rotated.text)
        self.assertEqual((await self.public.get(xml_path)).status_code, 404)
        new_path = urlsplit(rotated.json()["url"]).path
        self.assertTrue(new_path.endswith(".xml"))
        self.assertEqual((await self.public.get(new_path)).content, result.content)

    async def test_category_profiles_resolve_catalog_rules_and_publish_tree(
        self,
    ) -> None:
        """Проверяет одну версию настроек, стабильные ID, предпросмотр и три XML-профиля."""
        await crud_fixture.FeedCrudPostgresTests.seed_schema_locales(self)

        async def catalog_category(name: str, parent: str | None = None) -> str:
            response = await self.client.post(
                "/api/console/catalog/categories",
                headers=self.headers,
                json={"locale": "ru", "name": name, "parent_id": parent},
            )
            self.assertEqual(response.status_code, 201, response.text)
            return response.json()["id"]

        source_root = await catalog_category("Здоровье")
        source_child = await catalog_category("БАДы", source_root)
        item, other = await self.item(), await self.item()
        patched = await self.client.patch(
            f"{self.catalog}/{item}",
            headers=self.headers,
            json={"categories": {"primary_category_id": source_child}},
        )
        self.assertEqual(patched.status_code, 200, patched.text)

        root_id, child_id, fallback_id, unused_id = map(
            str, (uuid4(), uuid4(), uuid4(), uuid4())
        )
        rule_id = str(uuid4())
        node = {
            "id": child_id,
            "catalog_id": source_child,
            "inherit_parent": True,
            "name": " Биодобавки ",
            "export_id": "20",
            "portal_id": "12345",
            "rz_id": "67890",
            "attributes": {"featured": False},
            "elements": {"department_code": 0},
        }
        rules = [
            {
                "id": rule_id,
                "target_id": child_id,
                "label": "Категория и предки",
                "include_descendants": True,
                "condition": {
                    "kind": "comparison",
                    "operator": "CONTAINS",
                    "left": {"kind": "parameter", "parameter": "product.category_ids"},
                    "right": {
                        "kind": "scalar",
                        "value_type": "uuid",
                        "value": source_root,
                    },
                },
            }
        ]
        field = field_document(text_field("name"))
        field["type_definition"]["value"] = {
            "kind": "CONSTANT",
            "value": "Тестовое предложение",
        }

        for profile in ("PROM", "ROZETKA", "GENERIC"):
            with self.subTest(profile=profile):
                feed = await self.create(code=f"categories-{profile.lower()}", xml=True)
                self.root = f"{self.base}/{feed['id']}"
                self.path = f"{self.root}/publications"
                schema = {
                    "schema_format_version": 1,
                    "root": {"key": "publication", "kind": "object", "fields": [field]},
                    "categories": {
                        "version": 1,
                        "enabled": True,
                        "profile": profile,
                        "locale": "ru",
                        "nodes": [
                            {
                                "id": root_id,
                                "catalog_id": source_root,
                                "inherit_parent": True,
                            },
                            node,
                            {"id": fallback_id, "name": "Акции", "export_id": "30"},
                            {
                                "id": unused_id,
                                "name": "Пустая группа",
                                "export_id": "40",
                            },
                        ],
                        "rules": rules,
                        "fallback": "FIXED",
                        "fallback_id": fallback_id,
                        "name_transforms": [{"op": "string.trim", "params": {}}],
                        "attribute_types": {"featured": "boolean"},
                        "element_types": {"department_code": "number"},
                    },
                }
                saved = await self.client.put(
                    f"{self.root}/schema/draft",
                    headers=self.headers,
                    json={
                        "expected_version": 1,
                        "definition": schema_document(decode_schema(schema)),
                    },
                )
                self.assertEqual(saved.status_code, 200, saved.text)
                version = saved.json()["version"]
                persisted = saved.json()["definition"]["root"]["fields"][1][
                    "type_definition"
                ]["value"]
                self.assertEqual(persisted["nodes"][0]["values"]["id"], "1")
                self.assertEqual(
                    (await self.client.get(f"{self.root}/schema")).json()["definition"][
                        "root"
                    ]["fields"][1]["type_definition"]["value"],
                    persisted,
                )
                await self.add(
                    [{"catalog_item_id": item}, {"catalog_item_id": other}],
                    expected=version,
                )
                preview = await self.client.post(
                    f"{self.root}/preview",
                    headers=self.headers,
                    json={"expected_version": version},
                )
                self.assertEqual(preview.status_code, 200, preview.text)
                assignments = {
                    row["categories"][0]["export_id"]: row["categories"][0]
                    for row in preview.json()["rows"]
                }
                self.assertEqual(assignments["20"]["path"], ["Здоровье", "Биодобавки"])
                self.assertEqual(assignments["20"]["rule_label"], "Категория и предки")
                self.assertIsNone(assignments["30"]["rule_label"])

                await self.enqueue(version)
                await self.worker.process_once()
                state = await self.export_state()
                self.assertEqual(state["report"]["outcome"], "PUBLISHED", state)
                response = await self.public.get(urlsplit(state["active"]["url"]).path)
                self.assertEqual(response.status_code, 200, response.text)
                xml = ElementTree.fromstring(response.content)
                container = xml if profile == "GENERIC" else xml.find("shop")
                categories = {
                    item.get("id"): item
                    for item in container.findall("categories/category")
                }
                self.assertEqual(list(categories), ["1", "20", "30"])
                self.assertEqual(categories["20"].get("parentId"), "1")
                self.assertCountEqual(
                    [
                        item.findtext("categoryId")
                        for item in container.iterfind(".//offer")
                    ],
                    ["20", "30"],
                )
                if profile == "PROM":
                    self.assertEqual(
                        categories["20"].attrib,
                        {"id": "20", "parentId": "1", "portal_id": "12345"},
                    )
                elif profile == "ROZETKA":
                    self.assertEqual(
                        categories["20"].attrib,
                        {"id": "20", "parentId": "1", "rz_id": "67890"},
                    )
                else:
                    self.assertEqual(categories["20"].get("featured"), "false")
                    self.assertEqual(categories["20"].findtext("department_code"), "0")

    async def test_two_category_fields_export_tree_and_independent_reference(
        self,
    ) -> None:
        """Через API и фонового воркера проверяет два независимых выхода одного фида."""
        feed = await self.create(code="two-category-fields", xml=True)
        self.root = f"{self.base}/{feed['id']}"
        self.path = f"{self.root}/publications"
        root, shared = str(uuid4()), str(uuid4())

        def category(
            key: str, label: str, names: list[dict], records: list[dict], export: dict
        ) -> dict:
            """Готовит обычное поле с собственной схемой и записями."""
            return {
                "id": str(uuid4()),
                "key": key,
                "label": label,
                "export": {
                    "name": key,
                    "enabled": True,
                    "publication": {"value_key": "id", "required": True},
                }
                | export,
                "type_definition": {
                    "kind": "category",
                    "object_schema": {
                        "id_key": "id",
                        "label_key": "name",
                        "fields": names,
                    },
                    "value": {
                        "kind": "INLINE",
                        "nodes": records,
                        "rules": [],
                        "fallback": "FIXED",
                        "fallback_id": shared,
                    },
                },
            }

        id_and_label = [
            {
                "key": "id",
                "kind": "string",
                "required": True,
                "xml": {"placement": "ATTRIBUTE"},
            },
            {
                "key": "name",
                "kind": "text",
                "required": True,
                "xml": {"placement": "TEXT"},
            },
        ]
        first = category(
            "categoryId",
            "Каталог",
            id_and_label
            + [
                {
                    "key": "prom_id",
                    "kind": "string",
                    "xml": {"placement": "ATTRIBUTE", "name": "portal_id"},
                },
                {"key": "description", "kind": "text", "xml": {"placement": "ELEMENT"}},
            ],
            [
                {"id": root, "values": {"id": "10", "name": "Здоровье"}},
                {
                    "id": shared,
                    "parent_id": root,
                    "values": {
                        "id": "20",
                        "name": "Биодобавки",
                        "prom_id": "12345",
                        "description": 'Текст & "кавычки"',
                    },
                },
            ],
            {"document": {"container": "categories", "item": "category"}},
        )
        second = category(
            "warehouse_code",
            "Склад",
            [
                {"key": "id", "kind": "string", "required": True},
                {"key": "name", "kind": "string", "required": True},
                {"key": "code", "kind": "integer", "required": True},
            ],
            [{"id": shared, "values": {"id": "20", "name": "Основной", "code": 0}}],
            {
                "publication": {"value_key": "code", "required": True},
                "xml_placement": "ATTRIBUTE",
            },
        )
        version = await self.save_schema(1, [first, second])
        saved = (await self.client.get(f"{self.root}/schema")).json()["definition"]
        self.assertNotIn("categories", saved)
        self.assertEqual(
            [f["type_definition"]["kind"] for f in saved["root"]["fields"]],
            ["category", "category"],
        )
        await self.add([{"catalog_item_id": await self.item()}], expected=version)
        preview = await self.client.post(
            f"{self.root}/preview",
            headers=self.headers,
            json={"expected_version": version},
        )
        self.assertEqual(preview.status_code, 200, preview.text)
        row = preview.json()["rows"][0]
        self.assertEqual(row["values"], ["20", "0"])
        self.assertEqual(
            [c["path"] for c in row["categories"]],
            [["Здоровье", "Биодобавки"], ["Основной"]],
        )

        await self.enqueue(version)
        await self.worker.process_once()
        state = await self.export_state()
        self.assertEqual(state["report"]["outcome"], "PUBLISHED", state)
        output = await self.public.get(urlsplit(state["active"]["url"]).path)
        self.assertEqual(output.status_code, 200, output.text)
        xml = ElementTree.fromstring(output.content)
        nodes = xml.findall("categories/category")
        self.assertEqual([n.get("id") for n in nodes], ["10", "20"])
        self.assertEqual(
            nodes[1].attrib, {"id": "20", "portal_id": "12345", "parentId": "10"}
        )
        self.assertEqual(nodes[1].findtext("description"), 'Текст & "кавычки"')
        offer = xml.find("offer")
        self.assertEqual(offer.findtext("categoryId"), "20")
        self.assertEqual(offer.get("warehouse_code"), "0")
        self.assertEqual([child.tag for child in xml], ["categories", "offer"])

        second["export"]["document"] = {"container": "warehouses", "item": "warehouse"}
        second["type_definition"]["object_schema"]["fields"][2]["xml"] = {
            "placement": "ATTRIBUTE"
        }
        current = await self.client.get(self.root)
        self.assertEqual(current.status_code, 200, current.text)
        version = await self.save_schema(current.json()["version"], [first, second])
        await self.enqueue(version)
        await self.worker.process_once()
        state = await self.export_state()
        self.assertEqual(state["report"]["outcome"], "PUBLISHED", state)
        output = await self.public.get(urlsplit(state["active"]["url"]).path)
        self.assertEqual(output.status_code, 200, output.text)
        xml = ElementTree.fromstring(output.content)
        self.assertEqual([child.tag for child in xml], ["categories", "warehouses", "offer"])
        self.assertEqual(xml.find("warehouses/warehouse").attrib, {"code": "0"})
        self.assertEqual(xml.find("offer").findtext("categoryId"), "20")
        self.assertEqual(xml.find("offer").get("warehouse_code"), "0")

    async def test_static_text_is_available_in_schema_preview_and_export(self) -> None:
        """Выводит заданные тексты, включая атрибут предложения и многострочное значение."""
        selling_type = field_document(text_field("selling_type"))
        selling_type["export"]["xml_placement"] = "ATTRIBUTE"
        selling_type["type_definition"].update(
            value={"kind": "CONSTANT", "value": " r "},
            constraints={"required": True, "min_length": None, "max_length": 1},
            transforms=[{"op": "string.trim", "params": {}}],
        )
        description = field_document(text_field("description"))
        long_text = 'Первая строка\nВторая & "строка"'
        description["type_definition"].update(
            kind="text", value={"kind": "CONSTANT", "value": long_text}
        )
        fields = [selling_type, description]
        refs = [{"catalog_item_id": await self.item()} for _ in range(2)]
        for export_format in ("csv", "xml"):
            with self.subTest(export_format=export_format):
                feed = (
                    self.feed
                    if export_format == "csv"
                    else await self.create(code="text-xml", xml=True)
                )
                self.root = f"{self.base}/{feed['id']}"
                self.path = f"{self.root}/publications"
                version = await self.save_schema(1, fields)
                schema = await self.client.get(f"{self.root}/schema")
                self.assertEqual(schema.json()["definition"]["root"]["fields"], fields)
                added = await self.add(refs, expected=version)
                publication_id = added["items"][0]["id"]
                override = await self.client.put(
                    f"/api/console/feed-builder/publications/{publication_id}/overrides/{selling_type['id']}",
                    headers=self.headers,
                    json={
                        "value": "s",
                        "expected_version": 1,
                        "expected_feed_version": version,
                    },
                )
                self.assertEqual(override.status_code, 200, override.text)
                preview = await self.client.post(
                    f"{self.root}/preview",
                    headers=self.headers,
                    json={"expected_version": version},
                )
                self.assertEqual(preview.status_code, 200, preview.text)
                expected = [("r", long_text), ("s", long_text)]
                self.assertCountEqual(
                    [tuple(row["values"]) for row in preview.json()["rows"]], expected
                )

                await self.enqueue(version)
                await self.worker.process_once()
                state = await self.export_state()
                self.assertEqual(state["report"]["outcome"], "PUBLISHED", state)
                output = await self.public.get(urlsplit(state["active"]["url"]).path)
                self.assertEqual(output.status_code, 200, output.text)
                if export_format == "xml":
                    offers = ElementTree.fromstring(output.content)
                    self.assertTrue(
                        all(offer.find("selling_type") is None for offer in offers)
                    )
                    rows = [
                        (offer.get("selling_type"), offer.findtext("description"))
                        for offer in offers
                    ]
                else:
                    rows = [
                        tuple(row)
                        for row in csv.reader(StringIO(output.text), delimiter=";")
                    ]
                self.assertCountEqual(rows, expected)

    async def test_skip_invalid_publishes_valid_and_warning_items_in_both_formats(
        self,
    ) -> None:
        """Проверяет частичный успех, диагностику и сохранение старого файла."""
        await crud_fixture.FeedCrudPostgresTests.seed_schema_locales(self)
        required = field_document(
            text_field(
                "identifier",
                type_definition=StringFieldTypeVO(
                    ManualValueDefinitionVO(),
                    constraints=TextConstraintsVO(required=True),
                ),
            )
        )
        title = field_document(
            text_field(
                "title",
                type_definition=StringFieldTypeVO(
                    SourceValueDefinitionVO(
                        SourceReferenceVO(
                            SourceProvider.CATALOG, CatalogSourcePath.TITLE
                        )
                    ),
                    locale=LocaleCodeVO("uk"),
                    fallback_policy=LocaleFallbackPolicyVO(
                        LocaleFallbackMode.LOCALE_CHAIN, (LocaleCodeVO("ru"),)
                    ),
                ),
            )
        )
        reference = [{"catalog_item_id": await self.item()} for _ in range(3)]
        localized = await self.client.patch(
            f"{self.catalog}/{reference[1]['catalog_item_id']}?locale=ru",
            headers=self.headers,
            json={
                "content": {"expected_schema_version": 1, "values": {"title": "Резерв"}}
            },
        )
        self.assertEqual(localized.status_code, 200, localized.text)
        for format in ("csv", "xml"):
            with self.subTest(format=format):
                feed = (
                    self.feed
                    if format == "csv"
                    else await self.create(code="partial-xml", xml=True)
                )
                self.assertEqual(feed["export_settings"]["validation_policy"], "STRICT")
                self.root = f"{self.base}/{feed['id']}"
                self.path = f"{self.root}/publications"
                version = await self.save_schema(1, [required, title])
                added = await self.add(reference, expected=version)
                publications = {
                    item["catalog_item_id"]: item["id"] for item in added["items"]
                }

                version = await self.save_validation_policy(version, "SKIP_INVALID")
                await self.enqueue(version)
                await self.worker.process_once()
                first = await self.export_state()
                self.assertEqual(first["report"]["reason_code"], "ALL_ITEMS_REJECTED")
                self.assertIsNone(first["active"])

                version = await self.save_validation_policy(version, "STRICT")
                for item, value in zip(
                    reference[:2], ("VALID", "WARNING"), strict=True
                ):
                    publication = publications[item["catalog_item_id"]]
                    override = await self.client.put(
                        f"/api/console/feed-builder/publications/{publication}/overrides/{required['id']}",
                        headers=self.headers,
                        json={
                            "value": value,
                            "expected_version": 1,
                            "expected_feed_version": version,
                        },
                    )
                    self.assertEqual(override.status_code, 200, override.text)

                await self.enqueue(version)
                await self.worker.process_once()
                strict = await self.export_state()
                self.assertEqual(strict["report"]["reason_code"], "STRICT_REJECTED")
                self.assertIsNone(strict["active"])

                version = await self.save_validation_policy(version, "SKIP_INVALID")
                await self.enqueue(version)
                await self.worker.process_once()
                published = await self.export_state()
                report = published["report"]
                self.assertEqual(report["outcome"], "PUBLISHED")
                self.assertEqual(report["validation_policy"], "SKIP_INVALID")
                self.assertEqual(
                    tuple(
                        report[key]
                        for key in (
                            "total_items",
                            "valid_items",
                            "warning_items",
                            "rejected_items",
                        )
                    ),
                    (3, 1, 1, 1),
                )
                path = urlsplit(published["active"]["url"]).path
                self.assertTrue(path.endswith(f".{format}"))
                file = await self.public.get(path)
                self.assertEqual(file.status_code, 200, file.text)
                if format == "csv":
                    values = [
                        row[0] for row in csv.reader(StringIO(file.text), delimiter=";")
                    ]
                else:
                    values = [
                        row.findtext("identifier")
                        for row in ElementTree.fromstring(file.content)
                    ]
                self.assertCountEqual(values, ["VALID", "WARNING"])
                issues = await self.client.get(
                    f"{self.root}/export/issues?severity=ERROR"
                )
                self.assertEqual(issues.status_code, 200, issues.text)
                self.assertEqual(issues.json()["total"], 1)
                issue = issues.json()["items"][0]
                self.assertEqual(
                    issue["publication_id"],
                    publications[reference[2]["catalog_item_id"]],
                )
                self.assertEqual(issue["code"], "REQUIRED_VALUE_MISSING")

                narrowed = deepcopy(required)
                narrowed["type_definition"]["constraints"]["max_length"] = 1
                version = await self.save_schema(
                    published["feed_version"], [narrowed, title]
                )
                await self.enqueue(version)
                await self.worker.process_once()
                rejected = await self.export_state()
                self.assertEqual(
                    rejected["report"]["reason_code"], "ALL_ITEMS_REJECTED"
                )
                self.assertEqual(rejected["report"]["rejected_items"], 3)
                self.assertEqual(rejected["active"], published["active"])
                self.assertEqual((await self.public.get(path)).content, file.content)

    async def test_integer_and_boolean_across_preview_overrides_and_exports(
        self,
    ) -> None:
        """Проверяет наследуемый остаток, условия, типизированный override и оба формата."""
        parent = await self.item("variable")
        child = await self.item(parent=parent)
        zero = await self.item()
        untracked = await self.item()
        for item, quantity in ((parent, 1), (zero, 0)):
            stock = await self.client.patch(
                f"{self.catalog}/{item}",
                headers=self.headers,
                json={
                    "stock": {
                        "manage_stock": True,
                        "stock_quantity": quantity,
                        "stock_status": None,
                        "backorders": "no",
                    }
                },
            )
            self.assertEqual(stock.status_code, 200, stock.text)
        refs = [
            {"catalog_item_id": parent, "catalog_variant_id": child},
            {"catalog_item_id": zero},
            {"catalog_item_id": untracked},
        ]

        def field(name: str, kind: str, value: dict) -> dict:
            constraints = {"required": False}
            if kind == "integer":
                constraints.update(min_value=None, max_value=None)
            return {
                "id": str(uuid4()),
                "key": name,
                "label": name,
                "type_definition": {
                    "kind": kind,
                    "value": value,
                    "constraints": constraints,
                },
                "export": {"name": name, "enabled": True},
                "ai": {"instruction": None},
            }

        def source(path: str) -> dict:
            return {"kind": "SOURCE", "source": {"provider": "catalog", "path": path}}

        def condition(parameter: str, operator: str, number: str) -> dict:
            return {
                "kind": "comparison",
                "operator": operator,
                "left": {"kind": "parameter", "parameter": parameter},
                "right": {"kind": "decimal", "value": number},
            }

        quantity = field("quantity", "integer", source("item.stock_quantity"))
        available = field("available", "boolean", source("item.in_stock"))
        quantity["export"]["xml_placement"] = "ATTRIBUTE"
        available["export"]["xml_placement"] = "ATTRIBUTE"
        rule = field(
            "keep",
            "boolean",
            {
                "kind": "CALCULATED",
                "condition": {
                    "kind": "logical",
                    "operator": "ALL",
                    "operands": [
                        {
                            "kind": "presence",
                            "operator": "EXISTS",
                            "parameter": "stock.quantity",
                        },
                        condition("stock.quantity", "LT", "2"),
                        {
                            "kind": "logical",
                            "operator": "ANY",
                            "operands": [
                                condition("price.regular", "GT", "10"),
                                condition("price.regular", "EQ", "10"),
                            ],
                        },
                    ],
                },
                "then_value": True,
                "else_value": False,
            },
        )
        fixed = field("fixed", "integer", {"kind": "CONSTANT", "value": 0})
        inactive = field("inactive", "boolean", {"kind": "CONSTANT", "value": False})
        fields = [quantity, available, rule, fixed, inactive]

        for format in ("csv", "xml"):
            with self.subTest(format=format):
                feed = (
                    self.feed
                    if format == "csv"
                    else await self.create(code="scalar-xml", xml=True)
                )
                self.root = f"{self.base}/{feed['id']}"
                self.path = f"{self.root}/publications"
                version = await self.save_schema(1, fields)
                listed = await self.client.get(f"{self.root}/schema")
                self.assertEqual(listed.json()["definition"]["root"]["fields"], fields)
                for ref, expected in ((refs[0], True), (refs[2], False)):
                    response = await self.client.post(
                        f"{self.root}/calculation-preview",
                        headers=self.headers,
                        json={
                            "expected_version": version,
                            "field_id": rule["id"],
                            **ref,
                        },
                    )
                    self.assertEqual(response.status_code, 200, response.text)
                    self.assertIs(response.json()["resolved_value"], expected)

                added = await self.add(refs, expected=version)
                publication = next(
                    item["id"]
                    for item in added["items"]
                    if item["catalog_variant_id"] == child
                )
                endpoint = f"/api/console/feed-builder/publications/{publication}"
                for value, status in ((0, 422), (False, 200)):
                    override = await self.client.put(
                        f"{endpoint}/overrides/{available['id']}",
                        headers=self.headers,
                        json={
                            "expected_feed_version": version,
                            "expected_version": 1,
                            "value": value,
                        },
                    )
                    self.assertEqual(override.status_code, status, override.text)
                editor = await self.client.get(f"{endpoint}/fields")
                self.assertEqual(editor.status_code, 200, editor.text)
                detail = {entry["label"]: entry for entry in editor.json()["fields"]}
                self.assertEqual(detail["quantity"]["resolved_value"], 1)
                self.assertIs(detail["available"]["original_value"], True)
                self.assertIs(detail["available"]["resolved_value"], False)

                quantity_override = f"{endpoint}/overrides/{quantity['id']}"
                for value, status in ((False, 422), (0, 200)):
                    override = await self.client.put(
                        quantity_override,
                        headers=self.headers,
                        json={
                            "expected_feed_version": version,
                            "expected_version": 2,
                            "value": value,
                        },
                    )
                    self.assertEqual(override.status_code, status, override.text)
                editor = await self.client.get(f"{endpoint}/fields")
                self.assertEqual(editor.status_code, 200, editor.text)
                quantity_value = next(
                    field
                    for field in editor.json()["fields"]
                    if field["label"] == "quantity"
                )
                self.assertIs(type(quantity_value["resolved_value"]), int)
                self.assertEqual(quantity_value["resolved_value"], 0)
                reset = await self.client.delete(
                    quantity_override,
                    headers=self.headers,
                    params={"expected_feed_version": version, "expected_version": 3},
                )
                self.assertEqual(reset.status_code, 200, reset.text)

                await self.enqueue(version)
                await self.worker.process_once()
                state = await self.export_state()
                self.assertEqual(state["report"]["outcome"], "PUBLISHED", state)
                output = await self.public.get(urlsplit(state["active"]["url"]).path)
                self.assertEqual(output.status_code, 200, output.text)
                expected_rows = {
                    ("1", "false", "true", "0", "false"),
                    ("0", "false", "true", "0", "false"),
                    ("", "true", "false", "0", "false"),
                }
                if format == "csv":
                    rows = {
                        tuple(row)
                        for row in csv.reader(StringIO(output.text), delimiter=";")
                    }
                else:
                    offers = ElementTree.fromstring(output.content)
                    self.assertTrue(
                        all(offer.find("quantity") is None for offer in offers)
                    )
                    self.assertTrue(
                        all(offer.find("available") is None for offer in offers)
                    )
                    rows = {
                        (
                            offer.get("quantity", ""),
                            offer.get("available", ""),
                            *(
                                offer.findtext(key, "")
                                for key in ("keep", "fixed", "inactive")
                            ),
                        )
                        for offer in offers
                    }
                self.assertEqual(rows, expected_rows)

    async def test_first_strict_rejection_keeps_feed_unpublished(self) -> None:
        """Показывает первый отчёт без публичной ссылки и записи Storage."""
        required = text_field(
            "title",
            type_definition=StringFieldTypeVO(
                ManualValueDefinitionVO(), constraints=TextConstraintsVO(required=True)
            ),
        )
        version = await self.save_schema(1, [field_document(required)])
        await self.add([{"catalog_item_id": await self.item()}], expected=version)
        await self.enqueue(version)
        await self.worker.process_once()

        current = await self.export_state()
        self.assertEqual(current["report"]["outcome"], "REJECTED")
        self.assertEqual(current["report"]["rejected_items"], 1)
        self.assertIsNone(current["active"])
        self.assertIsNone(current["task"])
        self.assertFalse(current["can_rotate"])
        self.assertEqual((await self.client.get(self.root)).json()["status"], "DRAFT")
        async with self.scoped_session() as session:
            self.assertIsNone(await session.scalar(select(StoredFileModel.id)))

    async def test_refresh_rolls_back_state_and_job_when_scheduling_fails(self) -> None:
        """Проверяет атомарный rollback после первой записи в shared очередь."""
        version = await self.save_schema(1, [field_document(text_field("title"))])
        schedule = ScheduleScheduledJobUseCase.__call__

        async def fail_reconcile(self, command: ScheduleScheduledJobCommand):
            if command.job_type == RECONCILE_JOB_TYPE:
                raise RuntimeError("Scheduler unavailable.")
            return await schedule(self, command)

        with patch.object(ScheduleScheduledJobUseCase, "__call__", fail_reconcile):
            with self.assertRaisesRegex(RuntimeError, "Scheduler unavailable"):
                await self.enqueue(version)
        self.assertIsNone((await self.export_state())["task"])
        async with self.sessions() as session:
            queued = await session.scalar(
                select(ScheduledJobModel.id).where(
                    ScheduledJobModel.tenant_id == self.tenant.uuid
                )
            )
        self.assertIsNone(queued)
