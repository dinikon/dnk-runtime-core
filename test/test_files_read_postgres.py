"""Списки и сводка Files через реальный PostgreSQL и HTTP с trusted context."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
import os
import unittest
from unittest.mock import AsyncMock, Mock, patch
from uuid import UUID, uuid4

from fastapi import FastAPI, Request
from httpx import ASGITransport, AsyncClient
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool
from sqlalchemy.schema import CreateSchema, DropSchema

from src.modules.files.application.stored_file.file_category import (
    FileCategory,
    DOCUMENT_MIME_TYPES,
    classify_file,
)
from src.modules.files.application.port.storage import (
    StorageAdapterProtocol,
    StorageResolverProtocol,
)
from src.modules.files.application.stored_file.query.get_file_preview.handler import (
    GetFilePreviewHandler,
)
from src.modules.files.application.stored_file.query.get_file_preview.query import (
    GetFilePreviewQuery,
)
from src.modules.files.domain.error import FileNotFoundError
from src.modules.files.infrastructure.persistence.query_repository import (
    SqlAlchemyStorageQueryRepository,
)
from src.modules.files.domain.stored_file.aggregate import StoredFile
from src.modules.files.domain.value_object.file_name import FileNameVO
from src.modules.files.domain.value_object.file_size import FileSizeVO
from src.modules.files.infrastructure.persistence.models.bucket import BucketModel
from src.modules.files.infrastructure.persistence.models.storage_provider import (
    StorageProviderModel,
)
from src.modules.files.infrastructure.persistence.models.stored_file import (
    StoredFileModel,
)
from src.modules.files.infrastructure.stored_file.persistence.mapper import (
    StoredFileMapper,
)
from src.modules.files.presentation.router import router
from src.modules.identity.domain.auth.principal import Principal
from src.modules.identity.domain.auth.request_context import RequestContext
from src.modules.identity.presentation.auth.depends import get_optional_request_context
from src.modules.identity.application.access.authorization_service_protocol import (
    AuthorizationServiceProtocol,
)
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.shared.infrastructure.persistence.unit_of_work.sqlalchemy import (
    UnitOfWork,
)
from src.modules.shared.presentation.persistence.depends import get_uow
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_migrations import (
    TenantMigrator,
)

URL = os.environ.get("TEST_POSTGRES_URL")
PATHS = ("items", "trash", "overview", "providers", "buckets")


@unittest.skipUnless(URL, "Disposable PostgreSQL required")
class FilesReadPostgresTests(unittest.IsolatedAsyncioTestCase):
    """Проверяет SQL-проекции и HTTP-контракты без подключения к рабочим tenant."""

    async def asyncSetUp(self) -> None:
        """Создаёт два изолированных реестра и несколько дисков с разной готовностью."""
        self.engine = create_async_engine(URL, poolclass=NullPool)
        self.tenants = (uuid4(), uuid4())
        self.schemas = {
            tenant: f"dnk_files_read_{tenant.hex}" for tenant in self.tenants
        }
        self.now = datetime(2026, 10, 1, 12, tzinfo=UTC)
        self.buckets = (uuid4(), uuid4(), uuid4())
        self.foreign_bucket = uuid4()
        self.files: list[StoredFile] = []
        async with self.engine.begin() as connection:
            for tenant in self.tenants:
                await connection.execute(CreateSchema(self.schemas[tenant]))
                await TenantMigrator().upgrade(connection, self.schemas[tenant])
                await connection.execution_options(
                    schema_translate_map={"tenant": self.schemas[tenant]}
                )
                buckets = (
                    self.buckets
                    if tenant == self.tenants[0]
                    else (self.foreign_bucket,)
                )
                for position, bucket in enumerate(buckets):
                    provider = uuid4()
                    await connection.execute(
                        sa.insert(StorageProviderModel).values(
                            id=provider,
                            name=f"Provider {position}",
                            kind="minio",
                            is_system=position == 0,
                            config_ref="system_minio",
                        )
                    )
                    await connection.execute(
                        sa.insert(BucketModel).values(
                            id=bucket,
                            provider_id=provider,
                            name=f"dnk-tenant-{bucket.hex}",
                            status="preparing" if position == 2 else "ready",
                        )
                    )
        self.app = FastAPI()
        self.app.include_router(router, prefix="/api/console")
        self.app.state.context = self.context()
        self.app.dependency_overrides[get_optional_request_context] = (
            lambda: self.app.state.context
        )
        self.opened_uows = 0

        async def test_uow(request: Request) -> AsyncIterator[UnitOfWork]:
            """Передаёт всем repositories сессию доверенного tenant и завершает её до ответа."""
            self.opened_uows += 1
            tenant = UUID(request.app.state.context.principal.tenant_id)
            async with self.engine.connect() as connection:
                await connection.execution_options(
                    schema_translate_map={"tenant": self.schemas[tenant]}
                )
                async with UnitOfWork(
                    async_sessionmaker(connection, expire_on_commit=False)
                ) as uow:
                    yield uow

        self.app.dependency_overrides[get_uow] = test_uow
        self.client = AsyncClient(
            transport=ASGITransport(app=self.app), base_url="http://files.example"
        )

    async def asyncTearDown(self) -> None:
        """Закрывает HTTP-клиент и удаляет только UUID-схемы этого теста."""
        try:
            await self.client.aclose()
            async with self.engine.begin() as connection:
                for schema in self.schemas.values():
                    await connection.execute(
                        DropSchema(schema, cascade=True, if_exists=True)
                    )
        finally:
            await self.engine.dispose()

    def context(
        self, *, tenant: UUID | None = None, roles: tuple[str, ...] = ("admin",)
    ) -> RequestContext:
        """Создаёт тестовый trusted principal без tenant/user полей в HTTP-запросе."""
        return RequestContext(
            Principal(str(uuid4()), str(tenant or self.tenants[0]), "test", roles),
            None,
            None,
            None,
        )

    @asynccontextmanager
    async def session(self, tenant: UUID | None = None) -> AsyncIterator[AsyncSession]:
        """Открывает отдельную сессию для подготовки тестовых записей."""
        async with self.engine.connect() as connection:
            await connection.execution_options(
                schema_translate_map={"tenant": self.schemas[tenant or self.tenants[0]]}
            )
            async with AsyncSession(connection, expire_on_commit=False) as session:
                yield session

    async def add_file(
        self,
        name: str,
        *,
        mime: str = "application/pdf",
        size: int = 10,
        status: str = "ready",
        bucket: UUID | None = None,
        tenant: UUID | None = None,
        identifier: UUID | None = None,
        deleted: datetime | None = None,
    ) -> StoredFile:
        """Готовит состояние через фабрики/методы Domain и сохраняет тестовую запись."""
        file = StoredFile.create(
            file_id=EntityIdVO.from_value(identifier or uuid4()),
            bucket_id=EntityIdVO.from_value(bucket or self.buckets[0]),
            name=FileNameVO(name),
            content_type=mime,
            size=FileSizeVO(size),
            created_at=self.now,
        )
        if status != "uploading":
            file.mark_uploaded(size)
        if status in {"trashed", "purging"}:
            file.move_to_trash(EntityIdVO.from_value(uuid4()), deleted or self.now)
        if status == "purging":
            file.request_purge(deleted or self.now, EntityIdVO.from_value(uuid4()))
        async with self.session(tenant) as session:
            await session.execute(
                sa.insert(StoredFileModel).values(
                    **StoredFileMapper.to_insert_values(file)
                )
            )
            await session.commit()
        self.files.append(file)
        return file

    async def get(self, path: str, **params: object) -> dict:
        """Проверяет HTTP-успех и возвращает JSON своего сценария."""
        response = await self.client.get(f"/api/console/files/{path}/", params=params)
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    async def test_preview_filters_tenant_file_state_and_bucket_readiness(self) -> None:
        """Реальная SQL-проекция не открывает чужой файл, корзину или preparing-диск."""
        ready = await self.add_file("visible.pdf")
        hidden = [
            await self.add_file(f"{status}.pdf", status=status)
            for status in ("uploading", "trashed", "purging")
        ]
        hidden.append(await self.add_file("preparing.pdf", bucket=self.buckets[2]))
        hidden.append(
            await self.add_file(
                "foreign.pdf", tenant=self.tenants[1], bucket=self.foreign_bucket
            )
        )
        adapter = AsyncMock(spec=StorageAdapterProtocol)
        adapter.exists_owned.return_value = True
        resolver = Mock(spec=StorageResolverProtocol)
        resolver.resolve.return_value = adapter
        async with self.session() as session:
            handler = GetFilePreviewHandler(
                SqlAlchemyStorageQueryRepository(session), resolver
            )
            for file_id in [uuid4(), *(file.id.uuid for file in hidden)]:
                with self.assertRaises(FileNotFoundError):
                    await handler.execute(GetFilePreviewQuery(self.tenants[0], file_id))
            resolver.resolve.assert_not_called()
            result = await handler.execute(
                GetFilePreviewQuery(self.tenants[0], ready.id.uuid)
            )
            self.assertEqual(result.file_id, ready.id.uuid)
            self.assertEqual(result.content_type, "application/pdf")
            adapter.exists_owned.assert_awaited_once()
            adapter.open.assert_awaited_once()
            await result.stream.aclose()

    async def test_states_empty_pages_and_secret_free_metadata(self) -> None:
        """Списки разделены по состояниям; пустая страница сохраняет настоящий total."""
        for path in ("items", "trash"):
            empty = await self.get(path)
            self.assertEqual(
                empty, {"items": [], "total": 0, "page": 1, "page_size": 20}
            )
        for phase in ("ready", "uploading", "trashed", "purging"):
            await self.add_file(phase + ".pdf", status=phase)
        await self.add_file("hidden.pdf", bucket=self.buckets[2])
        active = await self.get("items")
        trash = await self.get("trash")
        self.assertEqual(active["total"], 1)
        self.assertEqual(
            {row["status"] for row in trash["items"]}, {"trashed", "purging"}
        )
        self.assertEqual(trash["total"], 2)
        for path, total in (("items", 1), ("trash", 2)):
            page = await self.get(path, page=10**30)
            self.assertEqual((page["total"], page["items"]), (total, []))
        self.assertEqual(
            set(active["items"][0]),
            {
                "file_id",
                "bucket_id",
                "bucket_name",
                "provider_id",
                "provider_name",
                "name",
                "content_type",
                "category",
                "size_bytes",
                "created_at",
            },
        )
        self.assertTrue(
            {"deleted_at", "purge_after", "purge_requested_at"}
            <= set(trash["items"][0])
        )
        for row in active["items"] + trash["items"]:
            self.assertTrue(
                {
                    "object_key",
                    "config_ref",
                    "deleted_by",
                    "purge_job_id",
                    "credentials",
                }.isdisjoint(row)
            )

    async def test_literal_search_unicode_case_trim_and_combined_filters(self) -> None:
        """Спецсимволы LIKE буквальные; фильтры диска и категории соединяются AND."""
        names = ("Звіт_100%.PDF", "ЗВІТ-100abc.PDF", "quote's.csv", "plain.pdf")
        for phase in ("ready", "trashed"):
            for name in names:
                await self.add_file(name, status=phase)
            await self.add_file(
                names[0], status=phase, bucket=self.buckets[1], mime="image/png"
            )
        for path in ("items", "trash"):
            for search, count in (
                ("%", 2),
                ("_", 2),
                ("\\", 0),
                ("  звіт_100%  ", 2),
                ("'", 1),
                ("%'; DROP TABLE files_registry; --", 0),
            ):
                with self.subTest(path=path, search=search):
                    result = await self.get(path, search=search)
                    self.assertEqual(result["total"], count)
            combined = await self.get(
                path, search="звіт", bucket_id=str(self.buckets[1]), category="images"
            )
            self.assertEqual(combined["total"], 1)
            mismatch = await self.get(
                path,
                search="звіт",
                bucket_id=str(self.buckets[1]),
                category="documents",
            )
            self.assertEqual(mismatch["total"], 0)
            self.assertEqual((await self.get(path, search=" " * 300))["total"], 5)

    async def test_stable_pagination_with_equal_dates_and_names(self) -> None:
        """ID стабилизирует порядок одинаковых дат/имён для активных файлов и корзины."""
        for phase in ("ready", "trashed"):
            for number in range(1, 24):
                await self.add_file(
                    "same.pdf",
                    status=phase,
                    identifier=UUID(int=number + (100 if phase == "trashed" else 0)),
                )
        for path, start in (("items", 0), ("trash", 100)):
            ids = []
            for page in (1, 2, 3):
                result = await self.get(path, page=page, page_size=10)
                self.assertEqual(result["total"], 23)
                self.assertEqual(len(result["items"]), 3 if page == 3 else 10)
                ids.extend(UUID(item["file_id"]).int for item in result["items"])
            self.assertEqual(ids, list(range(start + 23, start, -1)))
            for size in (20, 50, 100):
                self.assertEqual(
                    len((await self.get(path, page_size=size))["items"]), min(size, 23)
                )

    async def test_mime_classification_matches_lists_filters_and_overview(self) -> None:
        """Вся MIME-таблица нормализуется одинаково в active, trash и overview."""
        mimes = [
            *sorted(DOCUMENT_MIME_TYPES),
            "image/png",
            "video/mp4",
            "audio/mpeg",
            "application/zip",
            "text/unknown",
        ]
        expected = {category.value: 0 for category in FileCategory}
        for number, mime in enumerate(mimes):
            category = classify_file(mime).value
            expected[category] += 1
            for phase in ("ready", "trashed"):
                await self.add_file(
                    f"mime-{number}.dat",
                    mime=f"  {mime.upper()} ; charset=UTF-8",
                    status=phase,
                    size=3,
                )
        for path in ("items", "trash"):
            items = (await self.get(path, page_size=100))["items"]
            for item in items:
                self.assertEqual(
                    item["category"], classify_file(item["content_type"]).value
                )
            for category, count in expected.items():
                result = await self.get(path, category=category, page_size=100)
                self.assertEqual(result["total"], count)
                self.assertTrue(
                    all(item["category"] == category for item in result["items"])
                )
        overview = await self.get("overview")
        self.assertEqual(
            [item["category"] for item in overview["categories"]],
            [category.value for category in FileCategory],
        )
        self.assertEqual(
            {item["category"]: item["files_count"] for item in overview["categories"]},
            expected,
        )
        self.assertEqual(overview["active_size_bytes"], len(mimes) * 3)
        self.assertEqual(overview["trashed_size_bytes"], len(mimes) * 3)

    async def test_overview_counts_bucket_scope_and_exact_large_sizes(self) -> None:
        """Корзина включает purging; pending — её часть; размеры не теряют точность."""
        large = 2**53 + 1
        await self.add_file("large.pdf", size=large)
        await self.add_file("empty.png", mime="image/png", size=0)
        await self.add_file("trash.pdf", status="trashed", size=7)
        await self.add_file("pending.mp4", status="purging", mime="video/mp4", size=11)
        await self.add_file("uploading.pdf", status="uploading", size=100)
        await self.add_file(
            "second.jpg", mime="image/jpeg", bucket=self.buckets[1], size=5
        )
        all_disks = await self.get("overview", search="no match", category="videos")
        self.assertEqual(
            (all_disks["active_count"], all_disks["active_size_bytes"]), (3, large + 5)
        )
        self.assertEqual(
            (all_disks["trashed_count"], all_disks["trashed_size_bytes"]), (2, 18)
        )
        self.assertEqual(
            (all_disks["pending_purge_count"], all_disks["pending_purge_size_bytes"]),
            (1, 11),
        )
        first = await self.get("overview", bucket_id=str(self.buckets[0]))
        self.assertEqual(
            (first["active_count"], first["active_size_bytes"]), (2, large)
        )
        second = await self.get("overview", bucket_id=str(self.buckets[1]))
        self.assertEqual((second["active_count"], second["trashed_count"]), (1, 0))
        overview_empty_tenant = self.context(tenant=self.tenants[1])
        self.app.state.context = overview_empty_tenant
        empty = await self.get("overview")
        self.assertEqual(empty["active_count"], 0)
        self.assertTrue(
            all(
                item["files_count"] == item["size_bytes"] == 0
                for item in empty["categories"]
            )
        )

    async def test_bucket_filters_isolation_and_unready_statuses(self) -> None:
        """Повторяемые диски объединяются; чужой/отсутствующий ID дают одинаковый 404."""
        await self.add_file("first.pdf")
        await self.add_file("second.pdf", bucket=self.buckets[1])
        for path in ("items", "trash", "overview"):
            response = await self.client.get(
                f"/api/console/files/{path}/",
                params=[
                    ("bucket_id", str(self.buckets[0])),
                    ("bucket_id", str(self.buckets[1])),
                    ("bucket_id", str(self.buckets[1])),
                ],
            )
            self.assertEqual(response.status_code, 200, response.text)
            if path == "items":
                self.assertEqual(response.json()["total"], 2)
            missing = await self.client.get(
                f"/api/console/files/{path}/", params={"bucket_id": str(uuid4())}
            )
            foreign = await self.client.get(
                f"/api/console/files/{path}/",
                params={"bucket_id": str(self.foreign_bucket)},
            )
            self.assertEqual(
                (missing.status_code, missing.json()),
                (foreign.status_code, foreign.json()),
            )
            self.assertEqual(foreign.status_code, 404)
            self.assertEqual(
                (
                    await self.client.get(
                        f"/api/console/files/{path}/",
                        params={"bucket_id": str(self.buckets[2])},
                    )
                ).status_code,
                409,
            )
        same_id = uuid4()
        await self.add_file("local.pdf", identifier=same_id)
        await self.add_file(
            "foreign.pdf",
            tenant=self.tenants[1],
            bucket=self.foreign_bucket,
            identifier=same_id,
        )
        self.app.state.context = self.context(tenant=self.tenants[1])
        foreign = await self.get("items", tenant_id=str(self.tenants[0]))
        self.assertEqual(
            (foreign["total"], foreign["items"][0]["name"]), (1, "foreign.pdf")
        )

    async def test_http_validation_bounds_and_openapi_contracts(self) -> None:
        """HTTP отклоняет неверные поля; OpenAPI описывает отдельные Responses и GET без body."""
        for path in ("items", "trash"):
            for params in (
                {"page": 0},
                {"page_size": 11},
                {"page_size": "abc"},
                {"category": "audio"},
                {"search": "x" * 256},
                {"bucket_id": "not-a-uuid"},
            ):
                with self.subTest(path=path, params=params):
                    self.assertEqual(
                        (
                            await self.client.get(
                                f"/api/console/files/{path}/", params=params
                            )
                        ).status_code,
                        422,
                    )
        for path in ("items", "trash", "overview"):
            excessive = [("bucket_id", str(self.buckets[0]))] * 51
            response = await self.client.get(
                f"/api/console/files/{path}/", params=excessive
            )
            self.assertEqual(response.status_code, 422)
        openapi = self.app.openapi()
        for path in PATHS:
            contract = openapi["paths"][f"/api/console/files/{path}/"]["get"]
            self.assertTrue({"401", "403"} <= set(contract["responses"]))
        for path, response_name in (
            ("items", "ListFilesResponse"),
            ("trash", "ListTrashedFilesResponse"),
            ("overview", "GetFilesOverviewResponse"),
        ):
            contract = openapi["paths"][f"/api/console/files/{path}/"]["get"]
            self.assertNotIn("requestBody", contract)
            self.assertEqual(
                contract["responses"]["200"]["content"]["application/json"]["schema"][
                    "$ref"
                ],
                "#/components/schemas/" + response_name,
            )
            self.assertTrue(
                {"401", "403", "404", "409", "422"} <= set(contract["responses"])
            )
            self.assertTrue(
                {"tenant_id", "actor_id", "object_key"}.isdisjoint(
                    param["name"] for param in contract["parameters"]
                )
            )
            if path != "overview":
                page_size = next(
                    param
                    for param in contract["parameters"]
                    if param["name"] == "page_size"
                )
                self.assertEqual(page_size["schema"]["enum"], [10, 20, 50, 100])
            self.assertEqual(
                (
                    await self.client.post(f"/api/console/files/{path}/", json={})
                ).status_code,
                403 if path == "items" else 405,
            )
        self.assertEqual(
            (
                await self.client.get(f"/api/console/files/items/{uuid4()}/content/")
            ).status_code,
            404,
        )

    async def test_all_files_get_require_admin_even_with_allow_all_authorization(
        self,
    ) -> None:
        """Все пять GET отвергают member/anonymous и дополнительный authorization deny."""
        for roles in (("member",), (), ("administrator",)):
            self.app.state.context = self.context(roles=roles)
            for path in PATHS:
                self.assertEqual(
                    (await self.client.get(f"/api/console/files/{path}/")).status_code,
                    403,
                )
        self.app.state.context = RequestContext(None, None, None, None)
        for path in PATHS:
            self.assertEqual(
                (await self.client.get(f"/api/console/files/{path}/")).status_code, 401
            )
        self.app.state.context = RequestContext(
            Principal(str(uuid4()), None, "test", ("admin",)), None, None, None
        )
        for path in PATHS:
            self.assertEqual(
                (await self.client.get(f"/api/console/files/{path}/")).status_code, 403
            )
        self.assertEqual(self.opened_uows, 0)
        context = self.context()
        self.app.state.context = context
        service = AsyncMock(spec=AuthorizationServiceProtocol)
        service.can.return_value = False
        self.app.state.authorization_service = service
        for path in PATHS:
            self.assertEqual(
                (await self.client.get(f"/api/console/files/{path}/")).status_code, 403
            )
        self.assertEqual(self.opened_uows, 0)
        service.can.assert_awaited_with(
            user_id=UUID(context.principal.user_id),
            tenant_id=self.tenants[0],
            action="files.read",
            resource_type="stored_file",
            resource_id=None,
        )
        service.can.return_value = True
        for path in PATHS:
            self.assertEqual(
                (await self.client.get(f"/api/console/files/{path}/")).status_code, 200
            )

    async def test_default_lists_and_overview_are_single_statement_and_never_load_domain(
        self,
    ) -> None:
        """Count/items читаются одним statement; read-side не восстанавливает агрегат."""
        await self.add_file("ready.pdf")
        await self.add_file("trash.pdf", status="trashed")
        statements = []

        def capture(
            connection: object,
            cursor: object,
            statement: str,
            parameters: object,
            context: object,
            many: bool,
        ) -> None:
            """Считает SQL-команды запроса без вывода параметров или содержимого файлов."""
            statements.append(statement)

        sa.event.listen(self.engine.sync_engine, "before_cursor_execute", capture)
        try:
            with patch.object(
                StoredFile,
                "restore",
                side_effect=AssertionError("Read must not load aggregate"),
            ):
                for path in ("items", "trash", "overview"):
                    statements.clear()
                    await self.get(path)
                    self.assertEqual(len(statements), 1)
        finally:
            sa.event.remove(self.engine.sync_engine, "before_cursor_execute", capture)
