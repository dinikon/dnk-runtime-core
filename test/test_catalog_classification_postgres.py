"""HTTP, SQL и миграционные проверки классификации на настоящем PostgreSQL."""

import asyncio
import copy
import unittest
from dataclasses import replace
from uuid import uuid4
from alembic import command
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from test import test_catalog_variable_postgres as support
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_migrations import (
    TenantMigrator,
)


@unittest.skipUnless(
    support.support.URL, "TEST_POSTGRES_URL requires a disposable database"
)
class CatalogClassificationPostgresTests(unittest.IsolatedAsyncioTestCase):
    """Изолирует tenant и использует настоящие handler, UoW и CSRF."""

    asyncSetUp = support.CatalogVariablePostgresTests.asyncSetUp
    asyncTearDown = support.CatalogVariablePostgresTests.asyncTearDown
    request = support.CatalogVariablePostgresTests.request
    create_product = support.CatalogVariablePostgresTests.create_product
    attribute = support.CatalogVariablePostgresTests.attribute
    structure = support.CatalogVariablePostgresTests.structure
    variable = support.CatalogVariablePostgresTests.variable

    async def category(self, label: str, parent_id: str | None = None) -> dict:
        """Создаёт узел с явным родителем."""
        return await self.request(
            "POST",
            "/categories",
            {"locale": "en", "label": label, "parent_id": parent_id},
            201,
        )

    async def tag(self, label: str) -> dict:
        """Создаёт метку с серверным UUID."""
        return await self.request(
            "POST", "/tags", {"locale": "en", "label": label}, 201
        )

    async def test_category_tree_locales_move_revision_delete(self) -> None:
        """Ветви, пагинация, циклы, переводы и удаление родителей проверяются сервером."""
        a = await self.category("Root")
        b = await self.category("Child", a["id"])
        c = await self.category("Second")
        roots = await self.request(
            "GET", "/categories?locale=en&roots_only=true&page_size=1"
        )
        self.assertEqual(roots["total"], 2)
        self.assertEqual(len(roots["items"]), 1)
        branch = await self.request("GET", f"/categories?locale=en&parent_id={a['id']}")
        self.assertEqual([i["id"] for i in branch["items"]], [b["id"]])
        self.assertEqual(
            (await self.request("GET", f"/categories/{a['id']}?locale=en"))[
                "child_count"
            ],
            1,
        )
        await self.request(
            "PUT",
            f"/categories/{a['id']}/parent",
            {"expected_revision": 1, "parent_id": b["id"]},
            422,
        )
        await self.request(
            "PUT",
            f"/categories/{a['id']}/parent",
            {"expected_revision": 1, "parent_id": a["id"]},
            422,
        )
        await self.request(
            "DELETE", f"/categories/{a['id']}?expected_revision=1", status=409
        )
        await self.request(
            "PUT",
            f"/categories/{b['id']}/translations/ru",
            {"expected_revision": 1, "label": "Дочерняя"},
        )
        self.assertEqual(
            (await self.request("GET", f"/categories/{b['id']}?locale=en"))["label"],
            "Child",
        )
        await self.request(
            "PUT",
            f"/categories/{b['id']}/parent",
            {"expected_revision": 1, "parent_id": c["id"]},
            409,
        )
        await self.request(
            "PUT",
            f"/categories/{b['id']}/parent",
            {"expected_revision": 2, "parent_id": c["id"]},
        )
        await self.request(
            "DELETE", f"/categories/{a['id']}?expected_revision=1", status=204
        )
        await self.request("GET", f"/categories/{a['id']}?locale=en", status=404)
        await self.request(
            "PUT",
            f"/categories/{b['id']}/parent",
            {"expected_revision": 3, "parent_id": str(uuid4())},
            404,
        )
        await self.request(
            "PUT",
            f"/categories/{b['id']}/parent",
            {"expected_revision": 3, "parent_id": None},
        )

    async def test_general_values_independence_and_used_options(self) -> None:
        """Общие значения не меняют структуру VARIABLE и защищают определения/options."""
        product, attr = await self.variable()
        path = "/products/" + product["id"]
        original = copy.deepcopy(product)
        value = {
            "attribute_id": attr["id"],
            "option_id": attr["options"][2]["id"],
            "visible": False,
            "position": 2,
        }
        await self.request(
            "PUT", path + "/attributes", {"expected_revision": 1, "values": [value]}
        )
        saved = await self.request("GET", path + "?locale=en")
        for key in ["axes", "variants", "default_selection", "content"]:
            self.assertEqual(saved[key], original[key])
        self.assertEqual(saved["attribute_values"], [value])
        await self.request(
            "PUT",
            path + "/attributes",
            {"expected_revision": 2, "values": [value, value]},
            422,
        )
        await self.request(
            "PUT",
            path + "/attributes",
            {"expected_revision": 2, "values": [{**value, "option_id": str(uuid4())}]},
            422,
        )
        await self.request(
            "DELETE", "/attributes/" + attr["id"] + "?expected_revision=1", status=409
        )
        # SIMPLE protects an option used only by its general value, outside any axis.
        other = await self.attribute("material")
        simple = await self.create_product()
        sp = "/products/" + simple["id"]
        ov = {
            **value,
            "attribute_id": other["id"],
            "option_id": other["options"][2]["id"],
            "position": 0,
        }
        await self.request(
            "PUT", sp + "/attributes", {"expected_revision": 1, "values": [ov]}
        )
        options = [
            {"option_id": o["id"], "code": o["code"], "label": o["label"]}
            for o in other["options"][:2]
        ]
        await self.request(
            "PUT",
            "/attributes/" + other["id"] + "/options/en",
            {"expected_revision": 1, "options": options},
            409,
        )
        await self.request(
            "DELETE", "/attributes/" + other["id"] + "?expected_revision=1", status=409
        )
        await self.request(
            "PUT", sp + "/attributes", {"expected_revision": 2, "values": []}
        )
        await self.request(
            "PUT",
            "/attributes/" + other["id"] + "/options/en",
            {"expected_revision": 1, "options": options},
        )
        await self.request(
            "DELETE", "/attributes/" + other["id"] + "?expected_revision=2", status=204
        )

    async def test_product_assignments_primary_clear_and_kind_preservation(
        self,
    ) -> None:
        """Product сохраняет классификацию через контент, type и явные kind переходы."""
        product, attr = await self.variable()
        path = "/products/" + product["id"]
        a = await self.category("Root")
        b = await self.category("Leaf", a["id"])
        tag = await self.tag("Sale")
        await self.request(
            "PUT",
            path + "/categories",
            {
                "expected_revision": 1,
                "category_ids": [b["id"]],
                "primary_category_id": b["id"],
            },
        )
        await self.request(
            "PUT", path + "/tags", {"expected_revision": 2, "tag_ids": [tag["id"]]}
        )
        await self.request(
            "PUT",
            path + "/categories",
            {
                "expected_revision": 3,
                "category_ids": [b["id"]],
                "primary_category_id": None,
            },
            422,
        )
        await self.request(
            "PUT",
            path + "/categories",
            {
                "expected_revision": 3,
                "category_ids": [b["id"], b["id"]],
                "primary_category_id": b["id"],
            },
            422,
        )
        await self.request(
            "PUT",
            path + "/tags",
            {"expected_revision": 3, "tag_ids": [tag["id"], tag["id"]]},
            422,
        )
        await self.request(
            "DELETE", f"/categories/{b['id']}?expected_revision=1", status=409
        )
        await self.request(
            "DELETE", f"/tags/{tag['id']}?expected_revision=1", status=409
        )
        await self.request(
            "PUT",
            path + "/kind",
            {
                "expected_revision": 3,
                "structure": {
                    "kind": "simple",
                    "variant": {
                        "variant_id": product["variants"][0]["id"],
                        "virtual": False,
                    },
                },
            },
        )
        await self.request(
            "PUT",
            path + "/type",
            {"expected_revision": 4, "product_type_id": product["product_type_id"]},
        )
        saved = await self.request("GET", path + "?locale=en")
        self.assertEqual(saved["category_ids"], [b["id"]])
        self.assertEqual(saved["primary_category_id"], b["id"])
        self.assertEqual(saved["tag_ids"], [tag["id"]])
        # Ancestors were not implicitly assigned.
        self.assertNotIn(a["id"], saved["category_ids"])
        await self.request(
            "PUT",
            path + "/categories",
            {"expected_revision": 5, "category_ids": [], "primary_category_id": None},
        )
        await self.request(
            "PUT", path + "/tags", {"expected_revision": 6, "tag_ids": []}
        )
        await self.request(
            "DELETE", f"/categories/{b['id']}?expected_revision=1", status=204
        )
        await self.request(
            "DELETE", f"/tags/{tag['id']}?expected_revision=1", status=204
        )

    async def test_tenant_csrf_and_translation_search(self) -> None:
        """Ссылки другого tenant и запись без CSRF отвергаются; locale не подменяется."""
        a = await self.category("Root")
        tag = await self.tag("Discount")
        simple = await self.create_product()
        await self.request(
            "PUT",
            f"/tags/{tag['id']}/translations/ru",
            {"expected_revision": 1, "label": "Акция"},
        )
        self.assertEqual(
            (await self.request("GET", "/tags?locale=ru&search=Акция"))["total"], 1
        )
        self.assertEqual(
            (await self.request("GET", "/tags?locale=en&search=Акция"))["total"], 0
        )
        self.assertIsNone(
            (await self.request("GET", f"/tags/{tag['id']}?locale=de"))["label"]
        )
        response = await self.client.post(
            self.base + "/tags", json={"locale": "en", "label": "No csrf"}
        )
        self.assertEqual(response.status_code, 403)
        from src.modules.catalog.presentation.product.http.request.set_product_categories import (
            SetProductCategoriesRequest,
        )

        self.assertEqual(
            SetProductCategoriesRequest(
                expected_revision=1, category_ids=[], primary_category_id=None
            ).category_ids,
            (),
        )
        # The trusted request context switches to the second schema, not a body tenant field.
        original = self.context
        self.app.state.test_context = replace(
            original, principal=replace(original.principal, tenant_id=str(self.other))
        )
        try:
            await self.request("GET", f"/tags/{tag['id']}?locale=en", status=404)
            await self.request(
                "POST",
                "/categories",
                {"locale": "en", "label": "Foreign parent", "parent_id": a["id"]},
                404,
            )
            other = await self.create_product()
            await self.request(
                "PUT",
                "/products/" + other["id"] + "/categories",
                {
                    "expected_revision": 1,
                    "category_ids": [a["id"]],
                    "primary_category_id": a["id"],
                },
                404,
            )
            await self.request(
                "PUT",
                "/products/" + other["id"] + "/tags",
                {"expected_revision": 1, "tag_ids": [tag["id"]]},
                404,
            )
        finally:
            self.app.state.test_context = original
        self.assertEqual(
            (await self.request("GET", "/products/" + simple["id"] + "?locale=en"))[
                "revision"
            ],
            1,
        )

    async def test_competing_assignment_writes_have_one_winner(self) -> None:
        """Один lock и revision не допускают lost update между секциями Product."""
        simple = await self.create_product()
        tag = await self.tag("Sale")
        category = await self.category("Root")
        path = self.base + "/products/" + simple["id"]
        responses = await asyncio.gather(
            self.client.put(
                path + "/tags",
                headers=self.headers,
                json={"expected_revision": 1, "tag_ids": [tag["id"]]},
            ),
            self.client.put(
                path + "/categories",
                headers=self.headers,
                json={
                    "expected_revision": 1,
                    "category_ids": [category["id"]],
                    "primary_category_id": category["id"],
                },
            ),
        )
        self.assertEqual(sorted(r.status_code for r in responses), [200, 409])
        saved = await self.request("GET", "/products/" + simple["id"] + "?locale=en")
        self.assertEqual(saved["revision"], 2)
        self.assertEqual(bool(saved["tag_ids"]) + bool(saved["category_ids"]), 1)

    async def test_sql_constraints_primary_uniqueness_self_parent_and_membership(
        self,
    ) -> None:
        """SQL сохраняет FK, запрет parent=self и уникальность основной категории."""
        simple = await self.create_product()
        a = await self.category("A")
        b = await self.category("B", a["id"])
        await self.request(
            "PUT",
            "/products/" + simple["id"] + "/categories",
            {
                "expected_revision": 1,
                "category_ids": [a["id"]],
                "primary_category_id": a["id"],
            },
        )
        schema = self.schemas[0]
        for statement, params in [
            (
                f'INSERT INTO "{schema}".catalog_product_categories(product_id,category_id,is_primary) VALUES (:p,:c,true)',
                {"p": simple["id"], "c": b["id"]},
            ),
            (
                f'UPDATE "{schema}".catalog_categories SET parent_id=:a WHERE id=:a',
                {"a": a["id"]},
            ),
            (
                f'INSERT INTO "{schema}".catalog_product_categories(product_id,category_id,is_primary) VALUES (:p,:c,false)',
                {"p": simple["id"], "c": str(uuid4())},
            ),
            (
                f'INSERT INTO "{schema}".catalog_product_tags(product_id,tag_id) VALUES (:p,:t)',
                {"p": simple["id"], "t": str(uuid4())},
            ),
        ]:
            with self.assertRaises(IntegrityError):
                async with self.engine.begin() as connection:
                    await connection.execute(text(statement), params)
        self.assertIsNone(
            (await self.request("GET", f"/categories/{a['id']}?locale=en"))["parent_id"]
        )

    async def test_migrations_do_not_create_catalog_functions_or_triggers(self) -> None:
        """Свежие tenant-схемы не содержат пользовательских функций и триггеров Catalog."""
        for schema in self.schemas:
            async with self.engine.begin() as connection:
                functions = await connection.scalar(
                    text("""
                        SELECT count(*) FROM pg_proc p
                        JOIN pg_namespace n ON n.oid = p.pronamespace
                        WHERE n.nspname = :schema AND p.proname LIKE 'catalog_%'
                    """),
                    {"schema": schema},
                )
                triggers = await connection.scalar(
                    text("""
                        SELECT count(*) FROM pg_trigger t
                        JOIN pg_class c ON c.oid = t.tgrelid
                        JOIN pg_namespace n ON n.oid = c.relnamespace
                        WHERE n.nspname = :schema AND c.relname LIKE 'catalog_%'
                            AND NOT t.tgisinternal
                    """),
                    {"schema": schema},
                )
                self.assertEqual(functions, 0)
                self.assertEqual(triggers, 0)

    async def test_migration_preserves_existing_product_rows(self) -> None:
        """0018 -> 0019 сохраняет SIMPLE, VARIABLE, selections, IDs, контент и ревизии."""
        simple = await self.create_product()
        product, _ = await self.variable()
        schema = self.schemas[0]
        migrator = TenantMigrator()
        title = "c0000000-0000-4000-8000-000000000002"
        await self.request(
            "PUT",
            "/products/" + simple["id"] + "/content/en",
            {
                "expected_revision": 1,
                "expected_schema_version": 1,
                "values": {title: "Preserved SIMPLE"},
            },
        )
        await self.request(
            "PUT",
            "/products/" + product["id"] + "/content/ru",
            {
                "expected_revision": 1,
                "expected_schema_version": 1,
                "values": {title: "Сохранённый VARIABLE"},
            },
        )
        await self.request(
            "PUT",
            "/products/"
            + product["id"]
            + "/variants/"
            + product["variants"][0]["id"]
            + "/content/en",
            {
                "expected_revision": 2,
                "expected_schema_version": 1,
                "values": {title: "Variant override"},
            },
        )
        product = await self.request("GET", "/products/" + product["id"] + "?locale=en")
        # Use actual table names from the current schema, including content marker rows.
        async with self.engine.begin() as connection:
            names = (
                (
                    await connection.execute(
                        text("SELECT tablename FROM pg_tables WHERE schemaname=:s"),
                        {"s": schema},
                    )
                )
                .scalars()
                .all()
            )
            tables = [
                n
                for n in names
                if n.startswith("catalog_")
                and n
                not in {
                    "catalog_categories",
                    "catalog_category_translations",
                    "catalog_tags",
                    "catalog_tag_translations",
                    "catalog_product_categories",
                    "catalog_product_tags",
                    "catalog_product_attribute_values",
                }
            ]
            before = {
                t: [
                    dict(r)
                    for r in (
                        await connection.execute(
                            text(f'SELECT * FROM "{schema}"."{t}" ORDER BY 1,2')
                        )
                    )
                    .mappings()
                    .all()
                ]
                for t in tables
            }
            await migrator._migrate(
                connection, schema, command.downgrade, "0018_catalog_variable"
            )
            await migrator._migrate(
                connection, schema, command.upgrade, "0019_catalog_classification"
            )
            after = {
                t: [
                    dict(r)
                    for r in (
                        await connection.execute(
                            text(f'SELECT * FROM "{schema}"."{t}" ORDER BY 1,2')
                        )
                    )
                    .mappings()
                    .all()
                ]
                for t in tables
            }
            self.assertEqual(before, after)
        self.assertEqual(
            (await self.request("GET", "/products/" + simple["id"] + "?locale=en"))[
                "kind"
            ],
            "simple",
        )
        self.assertEqual(
            (await self.request("GET", "/products/" + product["id"] + "?locale=en"))[
                "variants"
            ],
            product["variants"],
        )
