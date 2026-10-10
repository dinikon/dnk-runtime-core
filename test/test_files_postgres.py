"""Настоящие PostgreSQL, MinIO и HTTP-контракты файлового сервиса."""

import asyncio
from datetime import UTC, datetime, timedelta
from io import BytesIO
import os
import unittest
from unittest.mock import patch, AsyncMock
from uuid import UUID, uuid4

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text, select, delete
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine, AsyncSession
from sqlalchemy.schema import CreateSchema, DropSchema
from sqlalchemy.pool import NullPool
from src.config import dnk_config
from src.modules.shared.infrastructure.persistence.global_migrations import (
    GlobalMigrator,
)
from src.modules.shared.infrastructure.persistence.unit_of_work.sqlalchemy import (
    UnitOfWork,
)
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_migrations import (
    TenantMigrator,
)
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_connection import (
    bind_tenant_schema,
)
from src.modules.tenancy.application.tenant.tenant_schema_naming import (
    TenantSchemaNaming,
)
from src.modules.tenancy.domain.tenant.value_object.tenant_id import TenantIdVO
from src.modules.tenancy.infrastructure.persistence.tenant import TenantModel
from src.modules.tenancy.infrastructure.adapter.files import FilesTenantStorageAdapter
from src.modules.tenancy.presentation.depends.storage_management import (
    prepare_tenant_storage,
)
from src.modules.files.infrastructure.assembly import build_files_handlers
from src.modules.files.presentation.router import router
from src.modules.files.infrastructure.storage.minio_adapter import MinioStorageAdapter
from src.modules.files.infrastructure.storage.resolver import StorageResolver
from src.modules.files.application.port.storage import (
    StorageLocation,
    StorageOwnershipError,
    StorageUnavailableError,
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
from src.modules.files.application.stored_file.command.upload_file.dto import (
    UploadFileResultDTO,
)
from src.modules.files.application.stored_file.command.upload_file.command import (
    UploadFileCommand,
)
from src.modules.files.application.stored_file.query.get_file_content.query import (
    GetFileContentQuery,
)
from src.modules.files.application.bucket.query.list_buckets.query import (
    ListBucketsQuery,
)
from src.modules.files.application.stored_file.command.cleanup_orphaned_objects.command import (
    CleanupOrphanedObjectsCommand,
)
from src.modules.files.domain.error import FileNotFoundError, InvalidFileError
from src.modules.identity.domain.auth.principal import Principal
from src.modules.identity.domain.auth.request_context import RequestContext
from src.modules.shared.infrastructure.persistence.tenant_cleanup import (
    delete_shared_tenant_records,
)
from test.crm_company_support import company_app
from test.files_consumer_support import (
    FilesAttachmentAdapter,
    AttachmentStorageProtocol,
)

URL = os.environ.get("TEST_POSTGRES_URL")


@unittest.skipUnless(
    URL and os.environ.get("TEST_MINIO_ENDPOINT"),
    "Disposable PostgreSQL and MinIO required",
)
class FilesPostgresTests(unittest.IsolatedAsyncioTestCase):
    """Проверяет изоляцию, внешние эффекты и восстановление durable подготовки."""

    async def asyncSetUp(self) -> None:
        """Создаёт две новые схемы и отдельные приватные контейнеры теста."""
        self.engine = create_async_engine(URL, poolclass=NullPool)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        self.naming = TenantSchemaNaming(dnk_config.SCHEMA_PREFIX)
        self.tenants = [uuid4(), uuid4()]
        self.adapter = MinioStorageAdapter(dnk_config.FILES)
        self.resolver = StorageResolver(
            {("minio", "system_minio"): lambda: self.adapter}
        )
        self.registrations = {}
        async with self.engine.begin() as connection:
            await GlobalMigrator().upgrade(connection)
            for tenant in self.tenants:
                schema = self.naming.schema_name(TenantIdVO.from_value(tenant))
                await connection.execute(CreateSchema(schema))
                await TenantMigrator().upgrade(connection, schema)
                await connection.execute(
                    TenantModel.__table__.insert().values(
                        id=tenant,
                        name=f"files-{tenant}",
                        external_id=str(tenant),
                        status="active",
                    )
                )
        for tenant in self.tenants:
            async with self.engine.connect() as connection:
                await bind_tenant_schema(connection, tenant, self.naming)
                async with AsyncSession(connection, expire_on_commit=False) as session:
                    handlers = build_files_handlers(session, self.resolver)
                    registration = await handlers.register.execute(
                        RegisterSystemStorageCommand(tenant)
                    )
                    await session.commit()
                    self.registrations[tenant] = registration
                    await handlers.provision.execute(
                        ProvisionSystemBucketCommand(tenant, registration.bucket_id)
                    )
                    await session.commit()

    async def asyncTearDown(self) -> None:
        """Удаляет только UUID этого теста и их физические ресурсы."""
        for tenant in self.tenants:
            registration = self.registrations.get(tenant)
            if registration:
                # Чистим ownership-метки, которые отдельный тест намеренно подменял.
                location = self.location(tenant)
                if await self.adapter.call(
                    lambda: self.adapter._client.bucket_exists(location.bucket_name)
                ):
                    await self.adapter.call(
                        lambda: self.adapter._client.set_bucket_tags(
                            location.bucket_name,
                            self.adapter._tags(
                                {
                                    "dnk_tenant": str(tenant),
                                    "dnk_bucket": str(location.bucket_id),
                                }
                            ),
                        )
                    )
                await self.adapter.purge(location)
        async with self.engine.begin() as connection:
            for tenant in self.tenants:
                await connection.execute(
                    DropSchema(
                        self.naming.schema_name(TenantIdVO.from_value(tenant)),
                        cascade=True,
                        if_exists=True,
                    )
                )
        async with self.sessions() as session:
            for tenant in self.tenants:
                await delete_shared_tenant_records(session, tenant)
            await session.execute(
                delete(TenantModel).where(TenantModel.id.in_(self.tenants))
            )
            await session.commit()
        await self.engine.dispose()

    def location(self, tenant: UUID) -> StorageLocation:
        """Возвращает конкретные координаты созданного тестового бакета."""
        return StorageLocation(
            tenant,
            self.registrations[tenant].bucket_id,
            f"dnk-tenant-{tenant.hex}",
            "minio",
            "system_minio",
        )

    async def upload(self, tenant: UUID, data: bytes) -> UploadFileResultDTO:
        """Загружает файл как внутренний бизнес-потребитель в общем UoW."""
        async with self.engine.connect() as connection:
            await bind_tenant_schema(connection, tenant, self.naming)
            async with UnitOfWork(
                async_sessionmaker(connection, expire_on_commit=False)
            ) as uow:
                return await build_files_handlers(
                    uow.session, self.resolver
                ).upload.execute(
                    UploadFileCommand(
                        tenant,
                        BytesIO(data),
                        len(data),
                        "example.bin",
                        "application/octet-stream",
                    )
                )

    async def test_register_stats_stream_and_multipart(self) -> None:
        """Повторная регистрация не дублируется; поток работает после закрытия UoW."""
        tenant = self.tenants[0]
        uploaded = []
        for data in (b"", b"hello", b"x" * (11 * 1024 * 1024)):
            result = await self.upload(tenant, data)
            uploaded.append(result)
            async with self.engine.connect() as connection:
                await bind_tenant_schema(connection, tenant, self.naming)
                async with UnitOfWork(
                    async_sessionmaker(connection, expire_on_commit=False)
                ) as uow:
                    content = await build_files_handlers(
                        uow.session, self.resolver
                    ).content.execute(GetFileContentQuery(tenant, result.file_id))
            try:
                chunks = [part async for part in content.stream]
                self.assertEqual(b"".join(chunks), data)
                self.assertTrue(all(len(part) <= 64 * 1024 for part in chunks))
            finally:
                await content.stream.aclose()
        async with self.engine.connect() as connection:
            await bind_tenant_schema(connection, tenant, self.naming)
            async with UnitOfWork(
                async_sessionmaker(connection, expire_on_commit=False)
            ) as uow:
                handlers = build_files_handlers(uow.session, self.resolver)
                self.assertEqual(
                    await handlers.register.execute(
                        RegisterSystemStorageCommand(tenant)
                    ),
                    self.registrations[tenant],
                )
                stats = await handlers.buckets.execute(ListBucketsQuery(tenant))
                self.assertEqual(
                    (stats[0].files_count, stats[0].size_bytes),
                    (3, 5 + 11 * 1024 * 1024),
                )

    async def test_other_tenant_and_anonymous_storage_access_are_denied(self) -> None:
        """ID чужого файла не раскрывается; anonymous S3-запрос запрещён."""
        left, right = self.tenants
        file = await self.upload(left, b"secret")
        async with self.engine.connect() as connection:
            await bind_tenant_schema(connection, right, self.naming)
            async with UnitOfWork(
                async_sessionmaker(connection, expire_on_commit=False)
            ) as uow:
                with self.assertRaises(FileNotFoundError):
                    await build_files_handlers(
                        uow.session, self.resolver
                    ).content.execute(GetFileContentQuery(right, file.file_id))
        async with AsyncClient() as client:
            response = await client.get(
                f'http://{os.environ["TEST_MINIO_ENDPOINT"]}/{self.location(left).bucket_name}/{file.file_id.hex}'
            )
            self.assertEqual(response.status_code, 403)
        fake = StorageLocation(
            right,
            self.location(left).bucket_id,
            self.location(left).bucket_name,
            "minio",
            "system_minio",
        )
        with self.assertRaises(StorageOwnershipError):
            await self.adapter.open(fake, file.file_id.hex)

    async def test_business_rollback_and_invalid_upload_leave_only_collectible_orphans(
        self,
    ) -> None:
        """Откат DB сохраняет бизнес-атомарность; cleanup не удаляет зарегистрированные файлы."""
        tenant = self.tenants[0]
        kept = await self.upload(tenant, b"kept")
        async with self.engine.connect() as connection:
            await bind_tenant_schema(connection, tenant, self.naming)
            with self.assertRaises(RuntimeError):
                async with UnitOfWork(
                    async_sessionmaker(connection, expire_on_commit=False)
                ) as uow:
                    handlers = build_files_handlers(uow.session, self.resolver)
                    consumer: AttachmentStorageProtocol = FilesAttachmentAdapter(
                        tenant, handlers.upload
                    )
                    orphan = await consumer.upload(BytesIO(b"orphan"), 6)
                    await uow.session.execute(
                        text(
                            f'CREATE TABLE "{self.naming.schema_name(TenantIdVO.from_value(tenant))}".consumer_attachment(file_id uuid REFERENCES "{self.naming.schema_name(TenantIdVO.from_value(tenant))}".files_registry(id))'
                        )
                    )
                    await uow.session.execute(
                        text(
                            f'INSERT INTO "{self.naming.schema_name(TenantIdVO.from_value(tenant))}".consumer_attachment VALUES (:id)'
                        ),
                        {"id": orphan.file_id},
                    )
                    raise RuntimeError("Business transaction failed")
            with self.assertRaises(InvalidFileError):
                async with UnitOfWork(
                    async_sessionmaker(connection, expire_on_commit=False)
                ) as uow:
                    await build_files_handlers(
                        uow.session, self.resolver
                    ).upload.execute(
                        UploadFileCommand(
                            tenant,
                            BytesIO(b"longer"),
                            2,
                            "invalid.bin",
                            "application/octet-stream",
                        )
                    )
            async with UnitOfWork(
                async_sessionmaker(connection, expire_on_commit=False)
            ) as uow:
                result = await build_files_handlers(
                    uow.session, self.resolver
                ).cleanup.execute(
                    CleanupOrphanedObjectsCommand(
                        tenant, datetime.now(UTC) + timedelta(seconds=1)
                    )
                )
                self.assertEqual(result.removed_objects, 2)
                stats = await build_files_handlers(
                    uow.session, self.resolver
                ).buckets.execute(ListBucketsQuery(tenant))
                self.assertEqual(stats[0].files_count, 1)
                with self.assertRaises(FileNotFoundError):
                    await build_files_handlers(
                        uow.session, self.resolver
                    ).content.execute(GetFileContentQuery(tenant, orphan.file_id))
        self.assertTrue(
            await self.adapter.call(
                lambda: self.adapter._client.stat_object(
                    self.location(tenant).bucket_name, kept.file_id.hex
                )
            )
        )

    async def test_resume_persists_registration_before_failure_and_reuses_bucket(
        self,
    ) -> None:
        """Сбой внешнего шага оставляет durable регистрацию для следующей попытки."""
        tenant = self.tenants[0]
        async with self.sessions() as session:
            await session.execute(
                text("UPDATE public.tenants SET status='provisioning' WHERE id=:id"),
                {"id": tenant},
            )
            await session.commit()
        with patch.object(
            self.adapter,
            "ensure_private_bucket",
            AsyncMock(side_effect=StorageUnavailableError("offline")),
        ):
            with self.assertRaises(StorageUnavailableError):
                await prepare_tenant_storage(
                    self.sessions,
                    self.naming,
                    tenant,
                    activate=True,
                    storage=self.resolver,
                )
        async with self.sessions() as session:
            self.assertEqual(
                (await session.get(TenantModel, tenant)).status, "provisioning"
            )
        await prepare_tenant_storage(
            self.sessions, self.naming, tenant, activate=True, storage=self.resolver
        )
        await prepare_tenant_storage(
            self.sessions, self.naming, tenant, activate=True, storage=self.resolver
        )
        async with self.sessions() as session:
            self.assertEqual((await session.get(TenantModel, tenant)).status, "active")
        self.assertEqual(
            await self.adapter.call(
                lambda: self.adapter._client.get_bucket_tags(
                    self.location(tenant).bucket_name
                )
            ),
            self.adapter._tags(
                {
                    "dnk_tenant": str(tenant),
                    "dnk_bucket": str(self.location(tenant).bucket_id),
                }
            ),
        )

    async def test_foreign_ownership_is_rejected_and_purge_is_idempotent(self) -> None:
        """Чужой контейнер не принимается; purge своего не затрагивает соседний tenant."""
        left, right = self.tenants
        location = self.location(left)
        await self.adapter.call(
            lambda: self.adapter._client.set_bucket_tags(
                location.bucket_name, self.adapter._tags({"owner": "foreign"})
            )
        )
        with self.assertRaises(StorageOwnershipError):
            await self.adapter.ensure_private_bucket(location)
        with self.assertRaises(StorageOwnershipError):
            await self.adapter.purge(location)
        await self.adapter.call(
            lambda: self.adapter._client.set_bucket_tags(
                location.bucket_name,
                self.adapter._tags(
                    {"dnk_tenant": str(left), "dnk_bucket": str(location.bucket_id)}
                ),
            )
        )
        await self.upload(left, b"left")
        await self.upload(right, b"right")
        await self.adapter.purge(location)
        await self.adapter.purge(location)
        self.assertFalse(
            await self.adapter.call(
                lambda: self.adapter._client.bucket_exists(location.bucket_name)
            )
        )
        self.assertTrue(
            await self.adapter.call(
                lambda: self.adapter._client.bucket_exists(
                    self.location(right).bucket_name
                )
            )
        )

    async def test_http_has_only_safe_read_projections(self) -> None:
        """Console API не раскрывает credentials и не разрешает запись или выдачу файлов."""
        tenant = self.tenants[0]
        context = RequestContext(
            Principal(str(uuid4()), str(tenant), "test", ("member",)), None, None, None
        )
        app = company_app(self.sessions, context, scoped_connection=True)
        app.include_router(router, prefix="/api/console")
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://tenant.example"
        ) as client:
            providers = await client.get("/api/console/files/providers/")
            buckets = await client.get("/api/console/files/buckets/")
            self.assertEqual((providers.status_code, buckets.status_code), (200, 200))
            self.assertEqual(
                set(providers.json()[0]), {"id", "name", "kind", "is_system"}
            )
            self.assertEqual(buckets.json()[0]["files_count"], 0)
            self.assertEqual(
                (
                    await client.post("/api/console/files/providers/", json={})
                ).status_code,
                405,
            )
            self.assertEqual(
                (
                    await client.get(f"/api/console/files/{uuid4()}/content/")
                ).status_code,
                404,
            )

    async def test_incomplete_multipart_cleanup_and_purge(self) -> None:
        """SDK list/abort совместим с реальным MinIO и учитывает возраст передачи."""
        tenant = self.tenants[0]
        location = self.location(tenant)
        key = uuid4().hex
        await self.adapter.call(
            lambda: self.adapter._client._create_multipart_upload(
                location.bucket_name, key, {}
            )
        )
        self.assertEqual(
            await self.adapter.abort_incomplete(
                location, datetime.now(UTC) - timedelta(hours=24)
            ),
            0,
        )
        self.assertEqual(
            await self.adapter.abort_incomplete(
                location, datetime.now(UTC) + timedelta(seconds=1)
            ),
            1,
        )
        await self.adapter.call(
            lambda: self.adapter._client._create_multipart_upload(
                location.bucket_name, uuid4().hex, {}
            )
        )
        await self.adapter.purge(location)
        self.assertFalse(
            await self.adapter.call(
                lambda: self.adapter._client.bucket_exists(location.bucket_name)
            )
        )
