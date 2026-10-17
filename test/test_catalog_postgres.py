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
                "expected_revision": 1,
                "expected_schema_version": 1,
                "values": {
                    "name": "Title",
                    "desc": "<p>Good</p><script>alert(1)</script>",
                },
            },
        )
        self.assertEqual(changed["revision"], 2)
        read = await self.request("GET", f"/items/{ident}?locale=en")
        self.assertEqual(read["item"]["content"]["name"], "Title")
        self.assertNotIn("<script", read["item"]["content"]["desc"])
        missing = await self.request("GET", f"/items/{ident}?locale=ru")
        self.assertIsNone(missing["item"]["content"])
        await self.request(
            "PUT",
            f"/items/{ident}/status",
            {"expected_revision": 1, "status": "active"},
            409,
        )
        # A parallel tenant cannot resolve the item identity.
        self.app.state.test_context = replace(
            self.context,
            principal=replace(self.context.principal, tenant_id=str(self.other)),
        )
        await self.request("GET", f"/items/{ident}?locale=en", status=404)

    async def test_measurement_contract_round_trip_and_legacy_rejection(self) -> None:
        """HTTP сохраняет единицы и точность, отклоняет старые режимы и неполные пары."""
        created = await self.create_item()
        ident = created["id"]
        body = {
            "expected_revision": 1,
            "weight": {"value": "0.000000001", "unit": "kg"},
            "dimensions": {
                "length": {"value": "12.5", "unit": "cm"},
                "width": None,
                "height": None,
            },
        }
        await self.request("PUT", f"/items/{ident}/measurements", body)
        item = (await self.request("GET", f"/items/{ident}?locale=en"))["item"]
        self.assertEqual(item["weight"]["unit"], "kg")
        self.assertEqual(item["dimensions"]["length"], {"value": "12.5", "unit": "cm"})
        self.assertIsNone(item["dimensions"]["height"])
        for weight in [
            "10",
            {"value": "1"},
            {"unit": "kg"},
            {"value": "1", "unit": "cm"},
            {"value": "0.0000000001", "unit": "kg"},
            {"mode": "set", "value": "1"},
        ]:
            await self.request(
                "PUT",
                f"/items/{ident}/measurements",
                {**body, "expected_revision": 2, "weight": weight},
                422,
            )
        await self.request(
            "PUT",
            f"/items/{ident}/measurements",
            {
                "expected_revision": 2,
                "weight": None,
                "dimensions": {"length": None},
            },
            422,
        )
        for section, payload in [
            ("price", {"price": {"mode": "clear"}}),
            ("virtual", {"virtual": {"mode": "set", "value": False}}),
            ("virtual", {"virtual": "false"}),
            ("stock", {"stock": None}),
            (
                "stock",
                {
                    "stock": {
                        "manage_stock": "parent",
                        "stock_quantity": None,
                        "stock_status": "in_stock",
                        "backorders": "no",
                    }
                },
            ),
        ]:
            await self.request(
                "PUT",
                f"/items/{ident}/{section}",
                {"expected_revision": 2, **payload},
                422,
            )
        await self.request(
            "PUT",
            f"/items/{ident}/stock",
            {
                "expected_revision": 2,
                "stock": {
                    "manage_stock": True,
                    "stock_quantity": -2,
                    "stock_status": None,
                    "backorders": "yes",
                },
            },
        )
        await self.request(
            "PUT",
            f"/items/{ident}/stock",
            {
                "expected_revision": 3,
                "stock": {
                    "manage_stock": False,
                    "stock_quantity": None,
                    "stock_status": "on_backorder",
                    "backorders": "no",
                },
            },
        )
        read = (await self.request("GET", f"/items/{ident}?locale=en"))["item"]
        self.assertEqual(read["stock_status"], "on_backorder")
        self.assertIsNone(read["stock"]["stock_quantity"])
        await self.request(
            "PUT",
            f"/items/{ident}/measurements",
            {"expected_revision": 4, "weight": None, "dimensions": None},
        )
        read = (await self.request("GET", f"/items/{ident}?locale=en"))["item"]
        self.assertIsNone(read["weight"])
        self.assertIsNone(read["dimensions"])

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
                "expected_revision": 1,
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
                "expected_revision": 2,
                "gallery": {"images": [], "primary_image_id": None},
            },
        )
        await self.request(
            "PUT",
            f"/items/{ident}/sku",
            {"expected_revision": 3, "sku": " SKU-1 "},
        )
        another = await self.create_item()
        await self.request(
            "PUT",
            f"/items/{another['id']}/sku",
            {"expected_revision": 1, "sku": "SKU-1"},
            409,
        )
        read = await self.request("GET", f"/items/{another['id']}?locale=en")
        self.assertEqual(read["item"]["revision"], 1)
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
                json={"expected_revision": 1, "status": status},
            )
            return response.status_code

        statuses = await asyncio.gather(change("active"), change("archived"))
        self.assertEqual(sorted(statuses), [200, 409])
        denied = await self.client.post(self.base + "/items/simple", json={})
        self.assertEqual(denied.status_code, 403)

    async def test_fresh_baseline_downgrade_upgrade_and_drift(self) -> None:
        """Сохранённая baseline обратима и совпадает с SQL metadata."""
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
                "expected_revision": 1,
                "expected_schema_version": 1,
                "values": {"name": "Kept"},
            },
        )
        async with self.engine.begin() as connection:
            await connection.execute(
                text("UPDATE public.ref_locales SET active=false WHERE code='en'")
            )
        result = await self.request("GET", f"/items/{ident}?locale=en")
        self.assertEqual(result["item"]["content"]["name"], "Kept")
        await self.request(
            "PUT",
            f"/items/{ident}/content/en",
            {
                "expected_revision": 2,
                "expected_schema_version": 1,
                "values": {"name": "Denied"},
            },
            422,
        )
        schema = self.schemas[0]
        for assignment in [
            "kind='variant',parent_id=id,product_type_id=NULL",
            "regular_price=1,currency=NULL",
            "weight='NaN'::numeric,weight_unit='g'",
            "manage_stock=true,stock_quantity=0,backorders=NULL",
            "weight=1,weight_unit=NULL",
            "length=1,length_unit='kg'",
            "height=0.0000000001,height_unit='m'",
            "width=-1,width_unit='cm'",
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
                data={"expected_revision": str(revision), "main": "false"},
            )
            self.assertEqual(uploaded.status_code, 201, uploaded.text)
            self.assertEqual(uploaded.json()["revision"], revision + 1)
            images.append(uploaded.json()["image_id"])
        read = await self.request("GET", f"/items/{ident}?locale=en")
        gallery = read["item"]["gallery"]
        self.assertEqual(gallery["primary_image_id"], images[0])
        primary = await self.request(
            "PUT",
            f"/items/{ident}/gallery/en/primary",
            {"expected_revision": 3, "image_id": images[1]},
        )
        self.assertEqual(primary, {"id": ident, "revision": 4})

        gallery["images"] = list(reversed(gallery["images"]))
        for position, image in enumerate(gallery["images"]):
            image["position"] = position
        gallery["primary_image_id"] = images[1]
        await self.request(
            "PUT",
            f"/items/{ident}/gallery/en",
            {"expected_revision": 4, "gallery": gallery},
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
            data={"expected_revision": "5", "alt": "x" * 1001},
        )
        self.assertEqual(rejected.status_code, 422)
        self.assertEqual(len(files.data), 2)
        # Removing a reference retains the Files object.
        await self.request(
            "PUT",
            f"/items/{ident}/gallery/en",
            {
                "expected_revision": 5,
                "gallery": {"images": [], "primary_image_id": None},
            },
        )
        self.assertEqual(len(files.data), 2)

    async def test_simple_sections_snapshot_and_removal(self) -> None:
        """Все сохранённые разделы используют одну ревизию, полные наборы и простой snapshot."""
        from datetime import UTC, datetime
        from uuid import UUID
        from src.modules.catalog.application.catalog_item.query.get_catalog_items_publication_snapshot.query import (
            GetCatalogItemsPublicationSnapshotQuery,
        )
        from src.modules.catalog.domain.catalog_item.value_object.identifier import (
            CatalogItemIdVO,
        )
        from src.modules.catalog.infrastructure.catalog_item.persistence.query_repository import (
            SqlAlchemyCatalogItemQueryRepository,
        )
        from src.modules.catalog.domain.error import CatalogConflictError

        created = await self.create_item()
        self.assertEqual(set(created), {"id", "revision"})
        ident, revision = created["id"], created["revision"]
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
        definition = await self.request(
            "GET", f"/attributes/{attribute['id']}?locale=en"
        )
        tag = await self.request("POST", "/tags", {"locale": "en", "label": "Tag"}, 201)
        sections = [
            ("status", {"status": "active"}),
            ("virtual", {"virtual": True}),
            ("sku", {"sku": " ZERO "}),
            ("price", {"price": {"regular_price": "0", "currency": "UAH"}}),
            (
                "attributes",
                {
                    "attributes": [
                        {
                            "attribute_id": attribute["id"],
                            "option_ids": [o["id"] for o in definition["options"]],
                            "visible": False,
                            "position": 0,
                        }
                    ]
                },
            ),
            ("tags", {"tag_ids": [tag["id"]]}),
            (
                "metadata",
                {
                    "metadata": [
                        {
                            "key": "enabled",
                            "value_type": "boolean",
                            "value": False,
                            "position": 0,
                        },
                        {
                            "key": "count",
                            "value_type": "decimal",
                            "value": "0",
                            "position": 1,
                        },
                    ]
                },
            ),
            (
                "content/en",
                {
                    "expected_schema_version": 1,
                    "values": {"name": "Simple", "desc": ""},
                },
            ),
            ("gallery/en", {"gallery": {"images": [], "primary_image_id": None}}),
        ]
        for section, body in sections:
            result = await self.request(
                "PUT",
                f"/items/{ident}/{section}",
                {"expected_revision": revision, **body},
            )
            revision += 1
            self.assertEqual(result, {"id": ident, "revision": revision})
        item = (await self.request("GET", f"/items/{ident}?locale=en"))["item"]
        self.assertEqual(item["price"], "0")
        self.assertTrue(item["available_for_sale"])
        self.assertEqual(item["sku"], "ZERO")
        self.assertFalse(item["metadata"][0]["value"])
        self.assertEqual(item["metadata"][1]["value"], "0")
        self.assertEqual(item["content"], {"name": "Simple", "desc": ""})
        self.assertFalse(
            {
                "own",
                "effective",
                "origins",
                "kind",
                "root_id",
                "root_revision",
                "parent_id",
                "axes",
                "selection",
                "default_selection",
                "price_min",
                "price_max",
            }
            & item.keys()
        )
        async with self.engine.connect() as connection:
            connection = await connection.execution_options(
                schema_translate_map={"tenant": self.schemas[0]},
                isolation_level="REPEATABLE READ",
            )
            async with async_sessionmaker(connection)() as session:
                repository = SqlAlchemyCatalogItemQueryRepository(session)
                query = GetCatalogItemsPublicationSnapshotQuery(
                    self.tenant,
                    (CatalogItemIdVO(UUID(ident)),),
                    "en",
                    expected_revisions={UUID(ident): revision},
                )
                snapshot = await repository.snapshot(query, datetime.now(UTC))
                self.assertEqual(snapshot.items[0].revision, revision)
                self.assertEqual(snapshot.items[0].content, item["content"])
                with self.assertRaises(CatalogConflictError):
                    await repository.snapshot(
                        replace(query, expected_revisions={UUID(ident): 1}),
                        datetime.now(UTC),
                    )
        async with self.engine.begin() as connection:
            await connection.execute(
                text(
                    f'INSERT INTO "{self.schemas[0]}".catalog_item_metadata (catalog_item_id,key,mode,value_type,text_value,decimal_value,boolean_value,position) VALUES (:id,:key,:mode,NULL,NULL,NULL,NULL,2)'
                ),
                {"id": UUID(ident), "key": "legacy", "mode": "clear"},
            )
        legacy_read = (await self.request("GET", f"/items/{ident}?locale=en"))["item"]
        self.assertEqual(len(legacy_read["metadata"]), 2)
        for section, body in [
            ("attributes", {"attributes": []}),
            ("tags", {"tag_ids": []}),
            ("metadata", {"metadata": []}),
        ]:
            await self.request(
                "PUT",
                f"/items/{ident}/{section}",
                {"expected_revision": revision, **body},
            )
            revision += 1
        for section in ("content/en", "gallery/en"):
            await self.request(
                "DELETE",
                f"/items/{ident}/{section}?expected_revision={revision}",
                status=204,
            )
            revision += 1
        item = (await self.request("GET", f"/items/{ident}?locale=en"))["item"]
        self.assertIsNone(item["content"])
        self.assertIsNone(item["gallery"])
        self.assertEqual(item["attributes"], [])
        self.assertEqual(item["metadata"], [])
        await self.request(
            "DELETE", f"/items/{ident}?expected_revision={revision}", status=204
        )
        await self.request("GET", f"/items/{ident}?locale=en", status=404)

    async def test_sql_variable_storage_is_preserved_and_inaccessible(self) -> None:
        """SQL хранит будущие семьи/оси/выборы, а все границы MVP работают только с simple."""
        from datetime import UTC, datetime
        from uuid import UUID
        from sqlalchemy import insert, select
        from sqlalchemy.exc import IntegrityError
        from src.modules.catalog.domain.catalog_item.aggregate import CatalogItem
        from src.modules.catalog.domain.catalog_item.value_object.identifier import (
            CatalogItemIdVO,
        )
        from src.modules.catalog.domain.error import CatalogNotFoundError
        from src.modules.catalog.infrastructure.catalog_item.persistence.mapper import (
            CatalogItemMapper,
        )
        from src.modules.catalog.infrastructure.catalog_item.persistence.repository import (
            SqlAlchemyCatalogItemRepository,
        )
        from src.modules.catalog.infrastructure.catalog_item.persistence.query_repository import (
            SqlAlchemyCatalogItemQueryRepository,
        )
        from src.modules.catalog.application.catalog_item.query.get_catalog_items_publication_snapshot.query import (
            GetCatalogItemsPublicationSnapshotQuery,
        )
        from src.modules.catalog.infrastructure.persistence.models.catalog_item import (
            CatalogItemModel,
        )
        from src.modules.catalog.infrastructure.persistence.models.catalog_item_attribute import (
            CatalogItemAttributeModel,
        )
        from src.modules.catalog.infrastructure.persistence.models.catalog_item_attribute_option import (
            CatalogItemAttributeOptionModel,
        )
        from src.modules.catalog.infrastructure.persistence.models.catalog_item_variant_selection import (
            CatalogItemVariantSelectionModel,
        )
        from src.modules.catalog.infrastructure.persistence.models.catalog_item_default_selection import (
            CatalogItemDefaultSelectionModel,
        )

        simple = await self.create_item()
        attribute = await self.request(
            "POST",
            "/attributes",
            {
                "code": "axis",
                "locale": "en",
                "label": "Axis",
                "options": [{"code": "a", "label": "A"}, {"code": "b", "label": "B"}],
            },
            201,
        )
        definition = await self.request(
            "GET", f"/attributes/{attribute['id']}?locale=en"
        )
        attribute_id = UUID(attribute["id"])
        options = tuple(UUID(o["id"]) for o in definition["options"])
        parent_id, first_id, second_id = uuid4(), uuid4(), uuid4()
        template = CatalogItemMapper.to_insert_values(
            CatalogItem.create_simple(
                CatalogItemIdVO(parent_id), self.actor, datetime.now(UTC)
            )
        )
        async with self.engine.begin() as connection:
            connection = await connection.execution_options(
                schema_translate_map={"tenant": self.schemas[0]}
            )
            await connection.execute(
                insert(CatalogItemModel), {**template, "kind": "variable"}
            )
            await connection.execute(
                insert(CatalogItemModel),
                [
                    {
                        **template,
                        "id": child,
                        "kind": "variant",
                        "parent_id": parent_id,
                        "product_type_id": None,
                    }
                    for child in (first_id, second_id)
                ],
            )
            await connection.execute(
                insert(CatalogItemAttributeModel),
                {
                    "catalog_item_id": parent_id,
                    "attribute_id": attribute_id,
                    "is_variation": True,
                    "mode": "set",
                    "visible": True,
                    "position": 0,
                },
            )
            await connection.execute(
                insert(CatalogItemAttributeOptionModel),
                [
                    {
                        "catalog_item_id": parent_id,
                        "attribute_id": attribute_id,
                        "option_id": option,
                        "is_variation": True,
                        "position": position,
                    }
                    for position, option in enumerate(options)
                ],
            )
            await connection.execute(
                insert(CatalogItemVariantSelectionModel),
                [
                    {
                        "catalog_item_id": child,
                        "parent_id": parent_id,
                        "attribute_id": attribute_id,
                        "option_id": option,
                        "is_variation": True,
                    }
                    for child, option in zip((first_id, second_id), options)
                ],
            )
            await connection.execute(
                insert(CatalogItemDefaultSelectionModel),
                {
                    "catalog_item_id": parent_id,
                    "attribute_id": attribute_id,
                    "option_id": options[0],
                    "is_variation": True,
                },
            )
        for identifier in (parent_id, first_id):
            await self.request("GET", f"/items/{identifier}?locale=en", status=404)
            await self.request(
                "PUT",
                f"/items/{identifier}/status",
                {"expected_revision": 1, "status": "active"},
                404,
            )
            await self.request(
                "DELETE", f"/items/{identifier}?expected_revision=1", status=404
            )
            await self.request(
                "GET", f"/items/{identifier}/images/en/{uuid4()}/content", status=404
            )
        listed = await self.request(
            "GET",
            f"/items?locale=en&include_variants=true&kind=variant&parent_id={parent_id}",
        )
        self.assertEqual([item["id"] for item in listed["items"]], [simple["id"]])
        self.assertEqual(listed["total"], 1)
        async with self.engine.connect() as connection:
            connection = await connection.execution_options(
                schema_translate_map={"tenant": self.schemas[0]}
            )
            async with async_sessionmaker(connection)() as session:
                with self.assertRaises(CatalogNotFoundError):
                    await SqlAlchemyCatalogItemRepository(session).get(
                        CatalogItemIdVO(parent_id)
                    )
                with self.assertRaises(CatalogNotFoundError):
                    await SqlAlchemyCatalogItemQueryRepository(session).snapshot(
                        GetCatalogItemsPublicationSnapshotQuery(
                            self.tenant, (CatalogItemIdVO(first_id),), "en"
                        ),
                        datetime.now(UTC),
                    )
                self.assertEqual(
                    len(
                        (
                            await session.execute(
                                select(CatalogItemVariantSelectionModel)
                            )
                        ).all()
                    ),
                    2,
                )
        # Deferred FK enforces the parent's role and membership of selected options.
        for statement, params in [
            (
                f'UPDATE "{self.schemas[0]}".catalog_item SET parent_id=:parent WHERE id=:child',
                {"parent": UUID(simple["id"]), "child": first_id},
            ),
            (
                f'UPDATE "{self.schemas[0]}".catalog_item_variant_selections SET option_id=:option WHERE catalog_item_id=:child',
                {"option": uuid4(), "child": first_id},
            ),
        ]:
            with self.assertRaises(IntegrityError):
                async with self.engine.begin() as connection:
                    await connection.execute(text(statement), params)

    async def test_removed_api_and_legacy_payloads_are_unavailable(self) -> None:
        """OpenAPI не рекламирует вариативность, старые body-контракты не принимаются."""
        schema = self.app.openapi()
        paths = schema["paths"]
        self.assertNotIn(self.base + "/items/variable", paths)
        self.assertFalse(
            any(path.endswith(("/variants", "/structure", "/kind")) for path in paths)
        )
        parameters = paths[self.base + "/items"]["get"].get("parameters", [])
        self.assertFalse(
            {"kind", "include_variants", "parent_id"} & {p["name"] for p in parameters}
        )
        created = await self.create_item()
        ident = created["id"]
        for method, path in [
            ("POST", "/items/variable"),
            ("GET", f"/items/{ident}/variants"),
            ("PUT", f"/items/{ident}/structure"),
            ("PUT", f"/items/{ident}/kind"),
        ]:
            response = await self.client.request(
                method, self.base + path, headers=self.headers, json={}
            )
            self.assertIn(response.status_code, {404, 405})
        for section, payload in [
            ("status", {"expected_root_revision": 1, "status": "active"}),
            (
                "content/en",
                {
                    "expected_revision": 1,
                    "expected_schema_version": 1,
                    "values": {"name": {"mode": "set", "value": "Name"}},
                },
            ),
            (
                "attributes",
                {
                    "expected_revision": 1,
                    "attributes": [
                        {
                            "attribute_id": str(uuid4()),
                            "option_ids": [],
                            "position": 0,
                            "mode": "clear",
                        }
                    ],
                },
            ),
            (
                "metadata",
                {
                    "expected_revision": 1,
                    "metadata": [
                        {
                            "key": "a",
                            "value_type": "text",
                            "value": "",
                            "position": 0,
                            "mode": "set",
                        }
                    ],
                },
            ),
        ]:
            await self.request("PUT", f"/items/{ident}/{section}", payload, 422)

    async def test_legacy_clear_only_metadata_is_deleted_on_save(self) -> None:
        """Пустой новый набор удаляет старую clear-запись даже без собственных значений."""
        from uuid import UUID

        created = await self.create_item()
        ident = created["id"]
        async with self.engine.begin() as connection:
            await connection.execute(
                text(
                    f'INSERT INTO "{self.schemas[0]}".catalog_item_metadata (catalog_item_id,key,mode,position) VALUES (:id,:key,:mode,0)'
                ),
                {"id": UUID(ident), "key": "legacy", "mode": "clear"},
            )
        item = (await self.request("GET", f"/items/{ident}?locale=en"))["item"]
        self.assertEqual(item["metadata"], [])
        await self.request(
            "PUT", f"/items/{ident}/metadata", {"expected_revision": 1, "metadata": []}
        )
        async with self.engine.connect() as connection:
            count = await connection.scalar(
                text(
                    f'SELECT count(*) FROM "{self.schemas[0]}".catalog_item_metadata WHERE catalog_item_id=:id'
                ),
                {"id": UUID(ident)},
            )
        self.assertEqual(count, 0)
