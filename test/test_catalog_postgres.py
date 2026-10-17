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
        self.tenant, self.other = (EntityIdVO(uuid4()), EntityIdVO(uuid4()))
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

    async def patch_section(
        self, item_id: str, section: str, body: dict | None = None, status: int = 200
    ) -> dict:
        """Строит PATCH из полного значения раздела для общей регрессии карточки."""
        body = dict(body or {})
        name, _, locale = section.partition("/")
        if name == "content":
            patch = {"content": body if body else None}
        elif name == "gallery":
            patch = body if body else {"gallery": None}
        elif name == "price":
            patch = (
                {"price_specification": body["price"]}
                if set(body) == {"price"}
                else body
            )
        else:
            patch = body
        return await self.request(
            "PATCH",
            f"/items/{item_id}" + (f"?locale={locale}" if locale else ""),
            patch,
            200 if status == 204 else status,
        )

    async def create_item(self) -> dict:
        return await self.request("POST", "/items", {}, 201)

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
        self.assertTrue(all((b["label"] is None for b in missing["schema"]["blocks"])))
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

    async def test_content_locale_and_sanitization(self) -> None:
        item = await self.create_item()
        ident = item["id"]
        changed = await self.patch_section(
            ident,
            f"content/en",
            {
                "expected_schema_version": 1,
                "values": {
                    "name": "Title",
                    "desc": "<p>Good</p><script>alert(1)</script>",
                },
            },
        )
        read = await self.request("GET", f"/items/{ident}?locale=en")
        self.assertEqual(read["item"]["content"]["name"], "Title")
        self.assertNotIn("<script", read["item"]["content"]["desc"])
        missing = await self.request("GET", f"/items/{ident}?locale=ru")
        self.assertIsNone(missing["item"]["content"])
        await self.patch_section(ident, f"status", {"status": "active"}, 200)
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
            "weight": {"value": "0.000000001", "unit": "kg"},
            "dimensions": {
                "length": {"value": "12.5", "unit": "cm"},
                "width": None,
                "height": None,
            },
        }
        await self.patch_section(ident, f"measurements", body)
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
            await self.patch_section(
                ident, f"measurements", {**body, "weight": weight}, 422
            )
        await self.patch_section(
            ident,
            f"measurements",
            {"weight": None, "dimensions": {"length": None}},
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
            await self.patch_section(ident, f"{section}", {**payload}, 422)
        await self.patch_section(
            ident,
            f"stock",
            {
                "stock": {
                    "manage_stock": True,
                    "stock_quantity": -2,
                    "stock_status": None,
                    "backorders": "yes",
                }
            },
        )
        await self.patch_section(
            ident,
            f"stock",
            {
                "stock": {
                    "manage_stock": False,
                    "stock_quantity": None,
                    "stock_status": "on_backorder",
                    "backorders": "no",
                }
            },
        )
        read = (await self.request("GET", f"/items/{ident}?locale=en"))["item"]
        self.assertEqual(read["stock_status"], "on_backorder")
        self.assertIsNone(read["stock"]["stock_quantity"])
        await self.patch_section(
            ident, f"measurements", {"weight": None, "dimensions": None}
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
        await self.patch_section(
            ident,
            f"categories",
            {"category_ids": [category["id"]], "primary_category_id": category["id"]},
        )
        await self.request("DELETE", f"/categories/{category['id']}", status=409)
        await self.patch_section(
            ident, f"gallery/en", {"gallery": {"images": [], "primary_image_id": None}}
        )
        await self.patch_section(ident, f"sku", {"sku": " SKU-1 "})
        another = await self.create_item()
        await self.patch_section(another["id"], f"sku", {"sku": "SKU-1"}, 409)
        read = await self.request("GET", f"/items/{another['id']}?locale=en")
        listed = await self.request(
            "GET", f"/items?locale=en&category_id={category['id']}"
        )
        self.assertEqual(listed["total"], 1)

    async def test_competing_writes_and_csrf(self) -> None:
        created = await self.create_item()
        ident = created["id"]

        async def change(status: str) -> int:
            response = await self.client.patch(
                self.base + f"/items/{ident}",
                headers=self.headers,
                json={"status": status},
            )
            return response.status_code

        statuses = await asyncio.gather(change("active"), change("archived"))
        self.assertEqual(sorted(statuses), [200, 200])
        denied = await self.client.post(self.base + "/items", json={})
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
        await self.patch_section(
            ident,
            f"content/en",
            {"expected_schema_version": 1, "values": {"name": "Kept"}},
        )
        async with self.engine.begin() as connection:
            await connection.execute(
                text("UPDATE public.ref_locales SET active=false WHERE code='en'")
            )
        result = await self.request("GET", f"/items/{ident}?locale=en")
        self.assertEqual(result["item"]["content"]["name"], "Kept")
        await self.patch_section(
            ident,
            f"content/en",
            {"expected_schema_version": 1, "values": {"name": "Denied"}},
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
                if any((i not in self.data for i in file_ids)):
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
                data={"main": "false"},
            )
            self.assertEqual(uploaded.status_code, 201, uploaded.text)
            images.append(uploaded.json()["image_id"])
        read = await self.request("GET", f"/items/{ident}?locale=en")
        gallery = read["item"]["gallery"]
        self.assertEqual(gallery["primary_image_id"], images[0])
        gallery = (await self.request("GET", f"/items/{ident}?locale=en"))["item"][
            "gallery"
        ]
        gallery["primary_image_id"] = images[1]
        primary = await self.request(
            "PATCH", f"/items/{ident}?locale=en", {"gallery": gallery}
        )
        self.assertEqual(primary, {"id": ident})
        gallery["images"] = list(reversed(gallery["images"]))
        for position, image in enumerate(gallery["images"]):
            image["position"] = position
        gallery["primary_image_id"] = images[1]
        await self.patch_section(ident, f"gallery/en", {"gallery": gallery})
        image = await self.client.get(
            self.base + f"/items/{ident}/images/en/{images[1]}/content"
        )
        self.assertEqual(image.status_code, 200, image.text)
        self.assertEqual(image.content, data)
        self.assertTrue(files.streams[-1].closed)
        await self.request(
            "GET", f"/items/{ident}/images/en/{uuid4()}/content", status=404
        )

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
            data={"alt": "x" * 1001},
        )
        self.assertEqual(rejected.status_code, 422)
        self.assertEqual(len(files.data), 2)
        await self.patch_section(
            ident, f"gallery/en", {"gallery": {"images": [], "primary_image_id": None}}
        )
        self.assertEqual(len(files.data), 2)

    async def test_simple_sections_snapshot_and_removal(self) -> None:
        """Все разделы используют единый PATCH, полные наборы и простой snapshot."""
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
        self.assertEqual(set(created), {"id"})
        ident = created["id"]
        attribute = await self.request(
            "POST",
            "/attributes",
            {
                "locale": "en",
                "label": "Color",
                "options": [
                    {"label": "Red"},
                    {"label": "Blue"},
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
            result = await self.patch_section(ident, f"{section}", {**body})
            self.assertEqual(result, {"id": ident})
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
                    self.tenant, (CatalogItemIdVO(UUID(ident)),), "en"
                )
                snapshot = await repository.snapshot(query, datetime.now(UTC))
                self.assertEqual(snapshot.items[0].content, item["content"])
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
            await self.patch_section(ident, f"{section}", {**body})
        for section in ("content/en", "gallery/en"):
            await self.patch_section(ident, f"{section}", status=204)
        item = (await self.request("GET", f"/items/{ident}?locale=en"))["item"]
        self.assertIsNone(item["content"])
        self.assertIsNone(item["gallery"])
        self.assertEqual(item["attributes"], [])
        self.assertEqual(item["metadata"], [])
        await self.request("DELETE", f"/items/{ident}", status=204)
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
                "locale": "en",
                "label": "Axis",
                "options": [{"label": "A"}, {"label": "B"}],
            },
            201,
        )
        definition = await self.request(
            "GET", f"/attributes/{attribute['id']}?locale=en"
        )
        attribute_id = UUID(attribute["id"])
        options = tuple((UUID(o["id"]) for o in definition["options"]))
        parent_id, first_id, second_id = (uuid4(), uuid4(), uuid4())
        template = CatalogItemMapper.to_insert_values(
            CatalogItem.create(
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
            await self.patch_section(identifier, f"status", {"status": "active"}, 404)
            await self.request("DELETE", f"/items/{identifier}", status=404)
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
            any((path.endswith(("/variants", "/structure", "/kind")) for path in paths))
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
                    "expected_schema_version": 1,
                    "values": {"name": {"mode": "set", "value": "Name"}},
                },
            ),
            (
                "attributes",
                {
                    "attributes": [
                        {
                            "attribute_id": str(uuid4()),
                            "option_ids": [],
                            "position": 0,
                            "mode": "clear",
                        }
                    ]
                },
            ),
            (
                "metadata",
                {
                    "metadata": [
                        {
                            "key": "a",
                            "value_type": "text",
                            "value": "",
                            "position": 0,
                            "mode": "set",
                        }
                    ]
                },
            ),
        ]:
            await self.patch_section(ident, f"{section}", payload, 422)

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
        await self.patch_section(ident, f"metadata", {"metadata": []})
        async with self.engine.connect() as connection:
            count = await connection.scalar(
                text(
                    f'SELECT count(*) FROM "{self.schemas[0]}".catalog_item_metadata WHERE catalog_item_id=:id'
                ),
                {"id": UUID(ident)},
            )
        self.assertEqual(count, 0)

    async def test_atomic_patch_fields_and_passive_sql_revision(self) -> None:
        """PATCH откатывает весь кандидат, различает null и пропуск, SQL revision пассивен."""
        from uuid import UUID

        item = await self.create_item()
        ident = item["id"]
        self.assertEqual(set(item), {"id"})
        await self.request("PATCH", f"/items/{ident}", {}, 422)
        await self.request(
            "PATCH", f"/items/{ident}", {"expected_revision": 1, "sku": "old"}, 422
        )
        for field in (
            "status",
            "virtual",
            "stock",
            "attributes",
            "metadata",
            "category_ids",
            "tag_ids",
        ):
            await self.request("PATCH", f"/items/{ident}", {field: None}, 422)
        failed = await self.client.patch(
            self.base + f"/items/{ident}?locale=en",
            headers=self.headers,
            json={
                "sku": "candidate",
                "virtual": True,
                "content": {"expected_schema_version": 1, "values": {"name": ""}},
            },
        )
        self.assertEqual(failed.status_code, 422)
        self.assertEqual(failed.json()["detail"]["errors"][0]["field"], "content")
        before = (await self.request("GET", f"/items/{ident}?locale=en"))["item"]
        self.assertIsNone(before["sku"])
        self.assertFalse(before["virtual"])
        await self.request("PATCH", f"/items/{ident}", {"content": None}, 422)
        await self.request(
            "PATCH",
            f"/items/{ident}?locale=en",
            {
                "sku": "atomic",
                "virtual": True,
                "price_specification": {"regular_price": "0", "currency": "UAH"},
                "content": {
                    "expected_schema_version": 1,
                    "values": {"name": "Saved", "desc": ""},
                },
            },
        )
        saved = (await self.request("GET", f"/items/{ident}?locale=en"))["item"]
        self.assertNotIn("revision", saved)
        await self.request(
            "PATCH", f"/items/{ident}", {"sku": "atomic", "virtual": True}
        )
        noop = (await self.request("GET", f"/items/{ident}?locale=en"))["item"]
        self.assertEqual(noop["updated_at"], saved["updated_at"])
        async with self.engine.begin() as connection:
            await connection.execute(
                text(
                    f'UPDATE "{self.schemas[0]}".catalog_item SET revision=17 WHERE id=:id'
                ),
                {"id": UUID(ident)},
            )
        await self.request("PATCH", f"/items/{ident}", {"sku": None})
        cleared = (await self.request("GET", f"/items/{ident}?locale=en"))["item"]
        self.assertIsNone(cleared["sku"])
        self.assertEqual(cleared["content"], saved["content"])
        async with self.engine.connect() as connection:
            revision = await connection.scalar(
                text(
                    f'SELECT revision FROM "{self.schemas[0]}".catalog_item WHERE id=:id'
                ),
                {"id": UUID(ident)},
            )
        self.assertEqual(revision, 17)
        await self.request(
            "PATCH", f"/items/{ident}?locale=en", {"content": None, "gallery": None}
        )
        await self.request("DELETE", f"/items/{ident}", status=204)

    async def test_parallel_patch_preserves_distinct_fields_and_sku_error_path(
        self,
    ) -> None:
        """Записи разных полей объединяются, занятый SKU возвращает привязанную ошибку."""
        item = await self.create_item()
        url = self.base + f'/items/{item["id"]}'
        responses = await asyncio.gather(
            self.client.patch(url, headers=self.headers, json={"sku": "parallel"}),
            self.client.patch(url, headers=self.headers, json={"virtual": True}),
        )
        self.assertEqual([r.status_code for r in responses], [200, 200])
        read = (await self.request("GET", f'/items/{item["id"]}?locale=en'))["item"]
        self.assertEqual(read["sku"], "parallel")
        self.assertTrue(read["virtual"])
        other = await self.create_item()
        failed = await self.client.patch(
            self.base + f'/items/{other["id"]}',
            headers=self.headers,
            json={"sku": "parallel", "virtual": True},
        )
        self.assertEqual(failed.status_code, 409)
        self.assertEqual(failed.json()["detail"]["errors"][0]["field"], "sku")
        other_read = (await self.request("GET", f'/items/{other["id"]}?locale=en'))[
            "item"
        ]
        self.assertFalse(other_read["virtual"])

    async def test_removed_section_routes_and_dictionary_revision_contracts(
        self,
    ) -> None:
        """OpenAPI не содержит старых записей и ревизий, справочники работают без них."""
        paths = self.app.openapi()["paths"]
        self.assertNotIn(self.base + "/items/simple", paths)
        for suffix in (
            "sku",
            "status",
            "virtual",
            "price",
            "stock",
            "measurements",
            "attributes",
            "categories",
            "tags",
            "metadata",
            "content/{locale}",
            "gallery/{locale}",
        ):
            self.assertNotIn(self.base + "/items/{item_id}/" + suffix, paths)
        for schema in self.app.openapi()["components"]["schemas"].values():
            self.assertFalse(
                {"revision", "expected_revision"} & schema.get("properties", {}).keys()
            )
        tag = await self.request(
            "POST", "/tags", {"locale": "en", "label": "Before"}, 201
        )
        self.assertEqual(set(tag), {"id"})
        changed = await self.request(
            "PUT", f'/tags/{tag["id"]}/translations/en', {"label": "After"}
        )
        self.assertEqual(set(changed), {"id"})
        read = await self.request("GET", f'/tags/{tag["id"]}?locale=en')
        self.assertEqual(read["label"], "After")
        self.assertNotIn("revision", read)

    async def test_attribute_ids_translations_and_replacement_without_codes(
        self,
    ) -> None:
        """HTTP сохраняет UUID и локали, защищает связи и отклоняет старые коды."""
        created = await self.request(
            "POST",
            "/attributes",
            {
                "locale": "en",
                "label": "Color",
                "options": [{"label": "Red"}, {"label": "Blue"}],
            },
            201,
        )
        attribute_id = created["id"]
        path = f"/attributes/{attribute_id}"
        english = await self.request("GET", path + "?locale=en")
        red, blue = english["options"]
        self.assertNotIn("code", english)
        self.assertTrue(all("code" not in option for option in english["options"]))
        await self.request(
            "POST", "/attributes", {"code": "old", "locale": "en", "label": "Old"}, 422
        )
        await self.request(
            "POST",
            "/attributes",
            {
                "locale": "en",
                "label": "Old",
                "options": [{"code": "old", "label": "Old"}],
            },
            422,
        )
        missing = await self.request("GET", path + "?locale=ru")
        self.assertIsNone(missing["label"])
        self.assertTrue(all(option["label"] is None for option in missing["options"]))
        await self.request("PUT", path + "/translations/ru", {"label": "Цвет"})
        await self.request(
            "PUT",
            path + "/options/ru",
            {
                "options": [
                    {"option_id": blue["id"]},
                    {"option_id": red["id"], "label": "Красный"},
                ]
            },
        )
        russian = await self.request("GET", path + "?locale=ru")
        self.assertEqual(
            [(o["id"], o["label"]) for o in russian["options"]],
            [(blue["id"], None), (red["id"], "Красный")],
        )
        english = await self.request("GET", path + "?locale=en")
        self.assertEqual([o["label"] for o in english["options"]], ["Blue", "Red"])
        await self.request(
            "PUT",
            path + "/options/ru",
            {
                "options": [
                    {"option_id": blue["id"], "label": "Синий"},
                    {"option_id": red["id"], "label": None},
                ]
            },
        )
        listing = await self.request("GET", "/attributes?locale=ru&search=Цвет")
        self.assertEqual([a["id"] for a in listing["items"]], [attribute_id])
        self.assertNotIn("code", listing["items"][0])
        self.assertEqual(
            (await self.request("GET", f"/attributes?locale=en&search={attribute_id}"))[
                "total"
            ],
            1,
        )
        self.assertEqual(
            (await self.request("GET", "/attributes?locale=en&search=Цвет"))["total"], 0
        )
        before = await self.request("GET", path + "?locale=ru")
        for invalid in (
            [{"option_id": red["id"]}, {"option_id": red["id"]}],
            [{"option_id": str(uuid4()), "label": "Foreign"}],
            [{"label": None}],
            [{"label": ""}],
            [{"option_id": red["id"], "code": "old", "label": "Old"}],
        ):
            await self.request("PUT", path + "/options/ru", {"options": invalid}, 422)
            self.assertEqual(await self.request("GET", path + "?locale=ru"), before)
        item = await self.create_item()
        await self.request(
            "PATCH",
            f'/items/{item["id"]}',
            {
                "attributes": [
                    {
                        "attribute_id": attribute_id,
                        "option_ids": [red["id"]],
                        "visible": True,
                        "position": 0,
                    }
                ]
            },
        )
        await self.request(
            "PUT",
            path + "/options/ru",
            {"options": [{"option_id": blue["id"], "label": "Синий"}]},
            409,
        )
        await self.request("DELETE", path, status=409)
        for name, schema in self.app.openapi()["components"]["schemas"].items():
            if "Attribute" in name:
                self.assertNotIn("code", schema.get("properties", {}), name)
        denied = await self.client.put(
            self.base + path + "/translations/en", json={"label": "Denied"}
        )
        self.assertEqual(denied.status_code, 403)
        self.app.state.test_context = replace(
            self.context,
            principal=replace(self.context.principal, tenant_id=str(self.other)),
        )
        await self.request("GET", path + "?locale=en", status=404)
        await self.request(
            "PUT", path + "/translations/en", {"label": "Foreign tenant"}, 404
        )

    async def test_attribute_code_migration_preserves_data_and_tenant_isolation(
        self,
    ) -> None:
        """Upgrade/downgrade/upgrade не меняет UUID, переводы, порядок и назначения."""
        from sqlalchemy import inspect

        attribute = await self.request(
            "POST",
            "/attributes",
            {
                "locale": "en",
                "label": "Color",
                "options": [{"label": "Red"}, {"label": "Blue"}],
            },
            201,
        )
        path = f'/attributes/{attribute["id"]}'
        await self.request("PUT", path + "/translations/ru", {"label": "Цвет"})
        definition = await self.request("GET", path + "?locale=en")
        option = definition["options"][0]["id"]
        await self.request(
            "PUT",
            path + "/options/ru",
            {
                "options": [
                    {
                        "option_id": o["id"],
                        "label": "Красный" if o["id"] == option else "Синий",
                    }
                    for o in definition["options"]
                ]
            },
        )
        item = await self.create_item()
        await self.request(
            "PATCH",
            f'/items/{item["id"]}',
            {
                "attributes": [
                    {
                        "attribute_id": attribute["id"],
                        "option_ids": [option],
                        "visible": False,
                        "position": 0,
                    }
                ]
            },
        )
        before = await self.request("GET", path + "?locale=ru")
        item_before = await self.request("GET", f'/items/{item["id"]}?locale=en')
        schema, other = self.schemas
        migrator = TenantMigrator()
        async with self.engine.begin() as connection:
            await migrator.downgrade(connection, schema, "0025_user_display_currency")
            await connection.execute(
                text(f"UPDATE \"{schema}\".catalog_attributes SET code='legacy_color'")
            )
            await migrator.upgrade(connection, schema)
            for table in ("catalog_attributes", "catalog_attribute_options"):
                for tenant_schema in (schema, other):
                    columns = await connection.run_sync(
                        lambda sync, s=tenant_schema, t=table: {
                            c["name"] for c in inspect(sync).get_columns(t, schema=s)
                        }
                    )
                    self.assertNotIn("code", columns)
            await migrator.downgrade(connection, schema, "0025_user_display_currency")
            restored = (
                await connection.execute(
                    text(f'SELECT id, code FROM "{schema}".catalog_attributes')
                )
            ).one()
            self.assertEqual(restored.code, "a_" + attribute["id"].replace("-", ""))
            codes = (
                (
                    await connection.execute(
                        text(f'SELECT code FROM "{schema}".catalog_attribute_options')
                    )
                )
                .scalars()
                .all()
            )
            self.assertEqual(len(set(codes)), 2)
            self.assertTrue(all(code.startswith("o_") for code in codes))
            await migrator.upgrade(connection, schema)
        self.assertEqual(await self.request("GET", path + "?locale=ru"), before)
        item_after = await self.request("GET", f'/items/{item["id"]}?locale=en')
        self.assertEqual(item_after["item"], item_before["item"])
        english_after = await self.request("GET", path + "?locale=en")
        self.assertEqual(
            [(o["id"], o["label"], o["position"]) for o in english_after["options"]],
            [(o["id"], o["label"], o["position"]) for o in definition["options"]],
        )
