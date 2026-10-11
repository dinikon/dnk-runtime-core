"""Реальный HTTP, табличное хранение и конкурирующие записи Catalog в PostgreSQL."""

import asyncio
import os
import unittest
from dataclasses import replace
from uuid import uuid4
from unittest.mock import patch
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool
from sqlalchemy.schema import CreateSchema, DropSchema
from src.config import dnk_config
from src.modules.identity.domain.auth.principal import Principal
from src.modules.identity.domain.auth.request_context import RequestContext
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.shared.infrastructure.persistence.global_migrations import (
    GlobalMigrator,
)
from src.modules.tenancy.application.tenant.tenant_schema_naming import (
    TenantSchemaNaming,
)
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_migrations import (
    TenantMigrator,
)
from src.modules.catalog.presentation.router import router
from src.modules.shared.infrastructure.persistence.unit_of_work.sqlalchemy import (
    UnitOfWork,
)
from test.crm_company_support import company_app

URL = os.environ.get("TEST_POSTGRES_URL")


@unittest.skipUnless(URL, "TEST_POSTGRES_URL requires a disposable database")
class CatalogPostgresTests(unittest.IsolatedAsyncioTestCase):
    """Проверяет срез на свежих tenant-схемах с настоящими UoW и CSRF."""

    async def asyncSetUp(self) -> None:
        """Создаёт две независимые tenant-схемы и доверенную HTTP-сборку."""
        self.engine = create_async_engine(URL, poolclass=NullPool)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        self.naming = TenantSchemaNaming(dnk_config.SCHEMA_PREFIX)
        self.tenant, self.other = EntityIdVO(uuid4()), EntityIdVO(uuid4())
        self.actor = EntityIdVO(uuid4())
        self.schemas = [self.naming.schema_name(t) for t in (self.tenant, self.other)]
        async with self.engine.begin() as connection:
            await GlobalMigrator().upgrade(connection)
            self.locale_activity: dict[str, bool] = dict(
                (
                    await connection.execute(
                        text(
                            "SELECT code, active FROM public.ref_locales WHERE code IN ('ru', 'en')"
                        )
                    )
                ).all()
            )
            for code in ["ru", "en"]:
                await connection.execute(
                    text(
                        "INSERT INTO public.ref_locales(code,language_code,name,active) VALUES (:code,:code,:code,true) ON CONFLICT(code) DO UPDATE SET active=true"
                    ),
                    {"code": code},
                )
            await connection.execute(
                text(
                    "INSERT INTO public.ref_currencies(code,numeric_code,name,minor_units,active) VALUES ('UAH','980','UAH',2,true) ON CONFLICT(code) DO UPDATE SET active=true"
                )
            )
            for schema in self.schemas:
                await connection.execute(CreateSchema(schema))
                await TenantMigrator().upgrade(connection, schema)
        self.context = RequestContext(
            Principal(str(self.actor), str(self.tenant), "test", ("member",)),
            None,
            None,
            None,
        )
        self.app = company_app(self.sessions, self.context, scoped_connection=True)
        self.app.include_router(router, prefix="/api/console")
        scheme = "http" if dnk_config.AUTH.allow_insecure_http else "https"
        origin = f"{scheme}://tenant.example"
        self.client = AsyncClient(
            transport=ASGITransport(app=self.app, raise_app_exceptions=True),
            base_url=origin,
        )
        token = (await self.client.get("/csrf")).json()["csrf_token"]
        self.headers = {"Origin": origin, "X-CSRF-Token": token}
        self.base = "/api/console/catalog"

    async def asyncTearDown(self) -> None:
        """Удаляет тестовые схемы и восстанавливает активность справочника locale."""
        await self.client.aclose()
        async with self.engine.begin() as connection:
            for schema in self.schemas:
                await connection.execute(
                    DropSchema(schema, cascade=True, if_exists=True)
                )
            for code in ["ru", "en"]:
                if code in self.locale_activity:
                    await connection.execute(
                        text(
                            "UPDATE public.ref_locales SET active=:active WHERE code=:code"
                        ),
                        {"code": code, "active": self.locale_activity[code]},
                    )
                else:
                    await connection.execute(
                        text("DELETE FROM public.ref_locales WHERE code=:code"),
                        {"code": code},
                    )
        await self.engine.dispose()

    async def request(
        self, method: str, path: str, body: dict | None = None, status: int = 200
    ) -> dict:
        """Проверяет HTTP-статус и возвращает конкретный результат."""
        response = await self.client.request(
            method, self.base + path, headers=self.headers, json=body
        )
        self.assertEqual(response.status_code, status, response.text)
        return response.json() if status != 204 and status < 500 else {}

    async def create_item(self) -> dict:
        return await self.request("POST", "/items/simple", {}, 201)

    async def test_fixed_default_schema_localized_labels(self) -> None:
        """Default и три блока имеют фиксированные подписи, без редактора схемы."""
        result = await self.request("GET", "/product-type/default?locale=ru")
        self.assertEqual(result["locale"], "ru")
        self.assertEqual(result["schema"]["label"], "Стандартный")
        self.assertEqual(
            [b["code"] for b in result["schema"]["blocks"]],
            ["name", "desc", "short_desc"],
        )
        self.assertEqual(
            [b["label"] for b in result["schema"]["blocks"]],
            ["Название", "Описание", "Краткое описание"],
        )
        missing = await self.request("GET", "/product-type/default?locale=fr")
        self.assertIsNone(missing["schema"]["label"])
        self.assertTrue(all(b["label"] is None for b in missing["schema"]["blocks"]))
        await self.request("GET", "/product-type/default", status=422)
        await self.request("GET", "/product-type/default?locale=bad_locale", status=422)

    async def test_read_snapshot_precedes_identity_sql(self) -> None:
        """Read isolation назначается до SQL аутентификации на общем UoW."""
        from src.modules.identity.presentation.auth.depends import (
            get_optional_request_context,
        )
        from src.modules.shared.presentation.persistence.depends import UoWDep

        created = await self.create_item()
        isolation: list[str] = []

        async def authenticate(uow: UoWDep) -> RequestContext:
            await uow.session.execute(text("SELECT 1"))
            isolation.append(
                await uow.session.scalar(text("SHOW transaction_isolation"))
            )
            return self.context

        self.app.dependency_overrides[get_optional_request_context] = authenticate
        await self.request("GET", f"/items/{created['id']}?locale=en")
        self.assertEqual(isolation, ["repeatable read"])

    async def test_content_revisions_locale_and_sanitization(self) -> None:
        item = await self.create_item()
        ident = item["id"]
        changed = await self.request(
            "PUT",
            f"/items/{ident}/content/en",
            {
                "expected_root_revision": 1,
                "expected_schema_version": 1,
                "values": {
                    "name": {"mode": "set", "value": "Title"},
                    "desc": {
                        "mode": "set",
                        "value": "<p>Good</p><script>alert(1)</script>",
                    },
                },
            },
        )
        self.assertEqual(changed["root_revision"], 2)
        read = await self.request("GET", f"/items/{ident}?locale=en")
        self.assertEqual(read["item"]["effective"]["content"]["name"], "Title")
        self.assertNotIn("<script", read["item"]["effective"]["content"]["desc"])
        missing = await self.request("GET", f"/items/{ident}?locale=ru")
        self.assertIsNone(missing["item"]["effective"]["content"])
        await self.request(
            "PUT",
            f"/items/{ident}/status",
            {"expected_root_revision": 1, "status": "active"},
            409,
        )
        # A parallel tenant cannot resolve the item identity.
        self.app.state.test_context = replace(
            self.context,
            principal=replace(self.context.principal, tenant_id=str(self.other)),
        )
        await self.request("GET", f"/items/{ident}?locale=en", status=404)

    async def test_single_table_structure_effective_and_stock(self) -> None:
        attribute = await self.request(
            "POST",
            "/attributes",
            {
                "code": "color",
                "locale": "en",
                "label": "Color",
                "options": [
                    {"code": "red", "label": "Red"},
                    {"code": "blue", "label": "Blue"},
                ],
            },
            201,
        )
        details = await self.request("GET", f"/attributes/{attribute['id']}?locale=en")
        options = [o["id"] for o in details["options"]]
        structure = {
            "axes": [
                {
                    "attribute_id": attribute["id"],
                    "option_ids": options,
                    "position": 0,
                    "visible": False,
                }
            ],
            "variants": [
                {"selection": [{"attribute_id": attribute["id"], "option_id": o}]}
                for o in options
            ],
        }
        created = await self.request(
            "POST", "/items/variable", {"structure": structure}, 201
        )
        root = created["id"]
        child = created["child_ids"][0]
        await self.request(
            "PUT",
            f"/items/{root}/price",
            {
                "expected_root_revision": 1,
                "price": {
                    "mode": "set",
                    "value": {"regular_price": "10.100001", "currency": "UAH"},
                },
            },
        )
        await self.request(
            "PUT",
            f"/items/{root}/stock",
            {
                "expected_root_revision": 2,
                "stock": {
                    "manage_stock": "own",
                    "stock_quantity": 0,
                    "backorders": "notify",
                },
            },
        )
        await self.request(
            "PUT",
            f"/items/{child}/stock",
            {"expected_root_revision": 3, "stock": {"manage_stock": "parent"}},
        )
        read = await self.request("GET", f"/items/{child}?locale=en")
        self.assertEqual(read["item"]["root_id"], root)
        self.assertEqual(read["item"]["effective"]["price"], "10.100001")
        self.assertEqual(read["item"]["stock_status"], "on_backorder")
        self.assertEqual(read["item"]["effective"]["stock_source_id"], root)
        self.assertFalse(read["item"]["effective"]["attributes"][0]["visible"])
        listed = await self.request("GET", f"/items/{root}/variants?locale=en&limit=1")
        self.assertEqual(listed["total"], 2)
        await self.request(
            "DELETE", f"/attributes/{attribute['id']}?expected_revision=1", status=409
        )

        # The public batch port keeps source revisions and rejects an outdated plan.
        from datetime import datetime, UTC
        from src.modules.catalog.domain.catalog_item.value_object.identifier import (
            CatalogItemIdVO,
        )
        from src.modules.catalog.application.catalog_item.query.get_catalog_items_publication_snapshot.query import (
            GetCatalogItemsPublicationSnapshotQuery,
        )
        from src.modules.catalog.infrastructure.catalog_item.persistence.query_repository import (
            SqlAlchemyCatalogItemQueryRepository,
        )
        from src.modules.catalog.domain.error import CatalogConflictError
        from src.modules.tenancy.infrastructure.tenant.persistence.tenant_connection import (
            bind_tenant_schema,
        )

        async with self.engine.connect() as connection:
            from uuid import UUID

            await bind_tenant_schema(connection, self.tenant.uuid, self.naming)
            async with UnitOfWork(
                async_sessionmaker(connection, expire_on_commit=False)
            ) as uow:
                await uow.session.execute(
                    text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ")
                )
                repository = SqlAlchemyCatalogItemQueryRepository(uow.session)
                query = GetCatalogItemsPublicationSnapshotQuery(
                    self.tenant,
                    (CatalogItemIdVO.from_value(child),),
                    "en",
                    expected_root_revisions={UUID(root): 4},
                )
                snapshot = await repository.snapshot(query, datetime.now(UTC))
                self.assertEqual(snapshot.items[0].root_revision, 4)
                self.assertEqual(
                    snapshot.items[0].effective.stock_source_id.uuid, UUID(root)
                )
                with self.assertRaises(CatalogConflictError):
                    await repository.snapshot(
                        replace(query, expected_root_revisions={UUID(root): 3}),
                        datetime.now(UTC),
                    )

        # A variable without its own price still exposes the currency of priced children.
        await self.request(
            "PUT",
            f"/items/{root}/status",
            {"expected_root_revision": 4, "status": "active"},
        )
        await self.request(
            "PUT",
            f"/items/{child}/status",
            {"expected_root_revision": 5, "status": "active"},
        )
        await self.request(
            "PUT",
            f"/items/{child}/price",
            {
                "expected_root_revision": 6,
                "price": {
                    "mode": "set",
                    "value": {"regular_price": "10.100001", "currency": "UAH"},
                },
            },
        )
        await self.request(
            "PUT",
            f"/items/{root}/price",
            {"expected_root_revision": 7, "price": {"mode": "clear"}},
        )
        listed = await self.request("GET", "/items?locale=en")
        row = next(i for i in listed["items"] if i["id"] == root)
        self.assertEqual(
            (row["price_min"], row["price_max"], row["currency"]),
            ("10.100001", "10.100001", "UAH"),
        )

    async def test_classification_gallery_and_unique_sku(self) -> None:
        item = await self.create_item()
        ident = item["id"]
        category = await self.request(
            "POST",
            "/categories",
            {"locale": "en", "label": "Category", "parent_id": None},
            201,
        )
        await self.request(
            "PUT",
            f"/items/{ident}/categories",
            {
                "expected_root_revision": 1,
                "category_ids": [category["id"]],
                "primary_category_id": category["id"],
            },
        )
        await self.request(
            "DELETE", f"/categories/{category['id']}?expected_revision=1", status=409
        )
        await self.request(
            "PUT",
            f"/items/{ident}/gallery/en",
            {
                "expected_root_revision": 2,
                "gallery": {"images": [], "primary_image_id": None},
            },
        )
        await self.request(
            "PUT",
            f"/items/{ident}/sku",
            {"expected_root_revision": 3, "sku": " SKU-1 "},
        )
        another = await self.create_item()
        await self.request(
            "PUT",
            f"/items/{another['id']}/sku",
            {"expected_root_revision": 1, "sku": "SKU-1"},
            409,
        )
        read = await self.request("GET", f"/items/{another['id']}?locale=en")
        self.assertEqual(read["item"]["root_revision"], 1)
        listed = await self.request(
            "GET", f"/items?locale=en&category_id={category['id']}"
        )
        self.assertEqual(listed["total"], 1)

    async def test_competing_writes_and_csrf(self) -> None:
        created = await self.create_item()
        ident = created["id"]

        async def change(status: str) -> int:
            response = await self.client.put(
                self.base + f"/items/{ident}/status",
                headers=self.headers,
                json={"expected_root_revision": 1, "status": status},
            )
            return response.status_code

        statuses = await asyncio.gather(change("active"), change("archived"))
        self.assertEqual(sorted(statuses), [200, 409])
        denied = await self.client.post(self.base + "/items/simple", json={})
        self.assertEqual(denied.status_code, 403)

    async def test_fresh_baseline_downgrade_upgrade_and_drift(self) -> None:
        from alembic.autogenerate import compare_metadata
        from alembic.migration import MigrationContext
        from src.modules.tenancy.infrastructure.tenant.persistence.tenant_migration_metadata import (
            migration_metadata,
        )

        async with self.engine.begin() as connection:
            schema = self.schemas[0]
            await TenantMigrator().downgrade(
                connection, schema, "0022_tenant_currency_settings"
            )
            self.assertIsNone(
                await connection.scalar(
                    text("SELECT to_regclass(:table)"),
                    {"table": schema + ".catalog_item"},
                )
            )
            self.assertIsNotNone(
                await connection.scalar(
                    text("SELECT to_regclass(:table)"),
                    {"table": schema + ".files_registry"},
                )
            )
            await TenantMigrator().upgrade(connection, schema)
            await connection.execute(
                text("SELECT set_config('search_path',:schema,true)"),
                {"schema": schema},
            )

            def compare(sync):
                old_default = sync.dialect.default_schema_name
                sync.dialect.default_schema_name = schema
                try:
                    return compare_metadata(
                        MigrationContext.configure(
                            sync, opts={"include_schemas": False, "compare_type": True}
                        ),
                        migration_metadata(),
                    )
                finally:
                    sync.dialect.default_schema_name = old_default

            differences = await connection.run_sync(compare)
            self.assertEqual(differences, [])

    async def test_inactive_locale_reads_and_sql_constraints(self) -> None:
        from sqlalchemy.exc import IntegrityError

        created = await self.create_item()
        ident = created["id"]
        await self.request(
            "PUT",
            f"/items/{ident}/content/en",
            {
                "expected_root_revision": 1,
                "expected_schema_version": 1,
                "values": {"name": {"mode": "set", "value": "Kept"}},
            },
        )
        async with self.engine.begin() as connection:
            await connection.execute(
                text("UPDATE public.ref_locales SET active=false WHERE code='en'")
            )
        result = await self.request("GET", f"/items/{ident}?locale=en")
        self.assertEqual(result["item"]["effective"]["content"]["name"], "Kept")
        await self.request(
            "PUT",
            f"/items/{ident}/content/en",
            {
                "expected_root_revision": 2,
                "expected_schema_version": 1,
                "values": {"name": {"mode": "set", "value": "Denied"}},
            },
            422,
        )
        schema = self.schemas[0]
        for assignment in [
            "kind='variant',parent_id=id,product_type_id=NULL",
            "price_mode='set',regular_price=1,currency=NULL",
            "weight_mode='set',weight='NaN'::numeric",
            "manage_stock='own',stock_quantity=0,backorders=NULL",
        ]:
            with self.assertRaises(IntegrityError):
                async with self.engine.begin() as connection:
                    await connection.execute(
                        text(
                            f'UPDATE "{schema}".catalog_item SET {assignment} WHERE id=:id'
                        ),
                        {"id": ident},
                    )

    async def test_batch_query_count_and_explain(self) -> None:
        from sqlalchemy import event

        for _ in range(12):
            await self.create_item()
        statements = []

        def capture(connection, cursor, statement, parameters, context, executemany):
            if statement.lstrip().upper().startswith("SELECT"):
                statements.append(statement)

        event.listen(self.engine.sync_engine, "before_cursor_execute", capture)
        try:
            single = await self.request("GET", "/items?locale=en&limit=1")
            single_count = len(statements)
            statements.clear()
            page = await self.request("GET", "/items?locale=en&limit=12")
            page_count = len(statements)
        finally:
            event.remove(self.engine.sync_engine, "before_cursor_execute", capture)
        self.assertEqual(single_count, page_count)
        self.assertEqual(len(page["items"]), 12)
        self.assertNotIn("own", page["items"][0])
        async with self.engine.begin() as connection:
            plan = await connection.scalar(
                text(
                    f'EXPLAIN (ANALYZE,FORMAT JSON) SELECT id FROM "{self.schemas[0]}".catalog_item WHERE parent_id IS NULL ORDER BY created_at DESC,id LIMIT 12'
                )
            )
            self.assertIn("Plan", plan[0])

    async def test_kind_transition_and_explicit_family_deletion(self) -> None:
        attr = await self.request(
            "POST",
            "/attributes",
            {
                "code": "size",
                "locale": "en",
                "label": "Size",
                "options": [{"code": "s", "label": "S"}, {"code": "m", "label": "M"}],
            },
            201,
        )
        details = await self.request("GET", f"/attributes/{attr['id']}?locale=en")
        options = [o["id"] for o in details["options"]]
        structure = {
            "axes": [
                {"attribute_id": attr["id"], "option_ids": options, "position": 0}
            ],
            "variants": [
                {"selection": [{"attribute_id": attr["id"], "option_id": o}]}
                for o in options
            ],
        }
        simple = await self.create_item()
        ident = simple["id"]
        await self.request(
            "PUT", f"/items/{ident}/sku", {"expected_root_revision": 1, "sku": "CARRY"}
        )
        await self.request(
            "PUT",
            f"/items/{ident}/content/en",
            {
                "expected_root_revision": 2,
                "expected_schema_version": 1,
                "values": {"name": {"mode": "set", "value": "Family"}},
            },
        )
        family = await self.request(
            "PUT",
            f"/items/{ident}/kind",
            {
                "expected_root_revision": 3,
                "kind": "variable",
                "structure": structure,
                "carry_to_index": 0,
            },
        )
        self.assertEqual(family["root_id"], ident)
        children = family["child_ids"]
        await self.request(
            "DELETE", f"/items/{ident}?expected_root_revision=4", status=422
        )
        # Materialization keeps root identity and deliberately discards all children.
        changed = await self.request(
            "PUT",
            f"/items/{ident}/kind",
            {
                "expected_root_revision": 4,
                "kind": "simple",
                "selected_item_id": children[0],
                "discarded_ids": children,
            },
        )
        result = await self.request("GET", f"/items/{ident}?locale=en")
        self.assertEqual(result["item"]["effective"]["content"]["name"], "Family")
        for child in children:
            await self.request("GET", f"/items/{child}?locale=en", status=404)
        self.assertEqual(changed["root_revision"], 5)
        await self.request(
            "DELETE", f"/items/{ident}?expected_root_revision=5", status=204
        )

    async def test_media_upload_order_primary_and_stream_close(self) -> None:
        from typing import BinaryIO
        from uuid import UUID
        from collections.abc import AsyncIterator
        from src.modules.catalog.application.catalog_item.port.files import (
            UploadedCatalogImageFile,
            CatalogImageFileContent,
        )
        from src.modules.catalog.presentation.catalog_item.depends import get_files
        from src.modules.catalog.domain.error import CatalogNotFoundError

        class Stream:
            def __init__(self, data: bytes) -> None:
                self.data = data
                self.closed = False

            def __aiter__(self) -> AsyncIterator[bytes]:
                async def chunks() -> AsyncIterator[bytes]:
                    yield self.data

                return chunks()

            async def aclose(self) -> None:
                self.closed = True

        class Files:
            def __init__(self) -> None:
                self.data: dict[UUID, bytes] = {}
                self.streams: list[Stream] = []

            async def upload(
                self,
                tenant_id: UUID,
                source: BinaryIO,
                size_bytes: int,
                name: str,
                content_type: str,
            ) -> UploadedCatalogImageFile:
                identifier = uuid4()
                self.data[identifier] = source.read()
                return UploadedCatalogImageFile(
                    identifier, name, content_type, size_bytes
                )

            async def ensure_images(
                self, tenant_id: UUID, file_ids: tuple[UUID, ...]
            ) -> None:
                if any(i not in self.data for i in file_ids):
                    raise CatalogNotFoundError("Missing image")

            async def content(
                self, tenant_id: UUID, file_id: UUID
            ) -> CatalogImageFileContent:
                stream = Stream(self.data[file_id])
                self.streams.append(stream)
                return CatalogImageFileContent(
                    file_id, "image.png", "image/png", len(stream.data), stream
                )

        files = Files()
        self.app.dependency_overrides[get_files] = lambda: files
        created = await self.create_item()
        ident = created["id"]
        import base64

        data = base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jR9sAAAAASUVORK5CYII="
        )
        images = []
        for revision in (1, 2):
            uploaded = await self.client.post(
                self.base + f"/items/{ident}/images/en/upload",
                headers=self.headers,
                files={"image": ("image.png", data, "image/png")},
                data={"expected_root_revision": str(revision), "main": "false"},
            )
            self.assertEqual(uploaded.status_code, 201, uploaded.text)
            self.assertEqual(uploaded.json()["root_revision"], revision + 1)
            images.append(uploaded.json()["image_id"])
        read = await self.request("GET", f"/items/{ident}?locale=en")
        gallery = read["item"]["own"]["galleries"]["en"]
        self.assertEqual(gallery["primary_image_id"], images[0])
        gallery["images"] = list(reversed(gallery["images"]))
        for position, image in enumerate(gallery["images"]):
            image["position"] = position
        gallery["primary_image_id"] = images[1]
        await self.request(
            "PUT",
            f"/items/{ident}/gallery/en",
            {"expected_root_revision": 3, "gallery": gallery},
        )
        image = await self.client.get(
            self.base + f"/items/{ident}/images/en/{images[1]}/content"
        )
        self.assertEqual(image.status_code, 200, image.text)
        self.assertEqual(image.content, data)
        self.assertTrue(files.streams[-1].closed)
        await self.request(
            "GET", f"/items/{ident}/images/en/{uuid4()}/content", status=404
        )

        # UoW failure before streaming still closes the opened Files resource.
        async def fail_commit(uow: UnitOfWork) -> None:
            raise RuntimeError("Test commit failure")

        with patch.object(UnitOfWork, "commit", fail_commit):
            with self.assertRaisesRegex(RuntimeError, "Test commit failure"):
                await self.client.get(
                    self.base + f"/items/{ident}/images/en/{images[1]}/content"
                )
        self.assertTrue(files.streams[-1].closed)
        rejected = await self.client.post(
            self.base + f"/items/{ident}/images/en/upload",
            headers=self.headers,
            files={"image": ("image.png", data, "image/png")},
            data={"expected_root_revision": "4", "alt": "x" * 1001},
        )
        self.assertEqual(rejected.status_code, 422)
        self.assertEqual(len(files.data), 2)
        # Removing a reference retains the Files object.
        await self.request(
            "PUT",
            f"/items/{ident}/gallery/en",
            {
                "expected_root_revision": 4,
                "gallery": {"images": [], "primary_image_id": None},
            },
        )
        self.assertEqual(len(files.data), 2)
