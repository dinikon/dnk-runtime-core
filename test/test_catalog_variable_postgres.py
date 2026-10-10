"""Реальный PostgreSQL, HTTP и UoW для VARIABLE и enum-определений."""

import copy
import unittest
from dataclasses import replace
from uuid import uuid4
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from test import test_catalog_postgres as support
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_migrations import (
    TenantMigrator,
)


@unittest.skipUnless(support.URL, "TEST_POSTGRES_URL requires a disposable database")
class CatalogVariablePostgresTests(unittest.IsolatedAsyncioTestCase):
    """Использует общую изолированную HTTP-сборку без повторения SIMPLE тестов."""

    asyncSetUp = support.CatalogPostgresTests.asyncSetUp
    asyncTearDown = support.CatalogPostgresTests.asyncTearDown
    request = support.CatalogPostgresTests.request
    create_product = support.CatalogPostgresTests.create_product

    async def attribute(self, code: str = "color") -> dict:
        """Создаёт enum с тремя options, включая не выбранное вариантами значение."""
        created = await self.request(
            "POST",
            "/attributes",
            {
                "code": code,
                "locale": "en",
                "label": code,
                "options": [
                    {"code": "red", "label": "Red"},
                    {"code": "blue", "label": "Blue"},
                    {"code": "green", "label": "Green"},
                ],
            },
            201,
        )
        return await self.request("GET", "/attributes/" + created["id"] + "?locale=en")

    def structure(self, attribute: dict) -> dict:
        """Готовит полную валидную структуру с двумя вариантами."""
        aid = attribute["id"]
        options = attribute["options"]
        return {
            "kind": "variable",
            "axes": [
                {
                    "attribute_id": aid,
                    "option_ids": [o["id"] for o in options],
                    "position": 0,
                }
            ],
            "default_selection": {aid: options[0]["id"]},
            "variants": [
                {"selection": {aid: o["id"]}, "virtual": bool(i)}
                for i, o in enumerate(options[:2])
            ],
        }

    async def variable(self, attribute: dict | None = None) -> tuple[dict, dict]:
        """Создаёт VARIABLE через собственный HTTP-сценарий."""
        attr = attribute or await self.attribute()
        created = await self.request(
            "POST", "/products/variable", {"structure": self.structure(attr)}, 201
        )
        return (
            await self.request("GET", "/products/" + created["id"] + "?locale=en"),
            attr,
        )

    async def test_variable_title_locales_and_scope_isolation(self) -> None:
        """Title наследуется динамически, override снимается, описание собственное."""
        product, _ = await self.variable()
        path = "/products/" + product["id"]
        variant = product["variants"][0]
        vpath = path + "/variants/" + variant["id"]
        default = (await self.request("GET", "/product-types?locale=en"))["items"][0]
        title = next(
            b["block_id"]
            for b in default["blocks"]
            if b["code"] == "title" and b["scope"] == "PRODUCT"
        )
        description = next(
            b["block_id"]
            for b in default["blocks"]
            if b["code"] == "description" and b["scope"] == "PRODUCT"
        )
        await self.request(
            "PUT",
            path + "/content/en",
            {
                "expected_revision": 1,
                "expected_schema_version": 1,
                "values": {title: "Shirt", description: "Parent description"},
            },
        )
        read = await self.request("GET", vpath + "?locale=en")
        self.assertIsNone(read["content"])
        self.assertEqual(
            (read["effective_title"], read["title_source"]), ("Shirt", "PRODUCT")
        )
        self.assertIsNone(
            (await self.request("GET", vpath + "?locale=ru"))["effective_title"]
        )
        await self.request(
            "PUT",
            vpath + "/content/en",
            {
                "expected_revision": 2,
                "expected_schema_version": 1,
                "values": {
                    description: "<script>bad()</script><p>Variant</p>",
                    title: "Red shirt",
                },
            },
        )
        read = await self.request("GET", vpath + "?locale=en")
        self.assertEqual(read["title_source"], "VARIANT")
        self.assertNotIn("script", read["content"][description])
        unchanged = await self.request("GET", path + "?locale=en")
        self.assertEqual(unchanged["content"][description], "Parent description")
        other = next(v for v in unchanged["variants"] if v["id"] != variant["id"])
        self.assertIsNone(other["content"])
        self.assertEqual(other["effective_title"], "Shirt")
        await self.request(
            "PUT",
            vpath + "/content/en",
            {
                "expected_revision": 3,
                "expected_schema_version": 1,
                "values": {description: "Own", title: ""},
            },
        )
        empty = await self.request("GET", vpath + "?locale=en")
        self.assertEqual(
            (empty["effective_title"], empty["title_source"]), ("", "VARIANT")
        )
        await self.request(
            "PUT",
            vpath + "/content/en",
            {
                "expected_revision": 4,
                "expected_schema_version": 1,
                "values": {description: "Own"},
            },
        )
        self.assertEqual(
            (await self.request("GET", vpath + "?locale=en"))["effective_title"],
            "Shirt",
        )
        await self.request(
            "PUT",
            path + "/content/en",
            {
                "expected_revision": 5,
                "expected_schema_version": 1,
                "values": {title: "Updated"},
            },
        )
        self.assertEqual(
            (await self.request("GET", vpath + "?locale=en"))["effective_title"],
            "Updated",
        )
        self.assertNotIn(
            title, (await self.request("GET", vpath + "?locale=en"))["content"]
        )
        await self.request(
            "DELETE", path + "/content/en?expected_revision=6", status=204
        )
        read = await self.request("GET", vpath + "?locale=en")
        self.assertEqual(read["content"], {description: "Own"})
        self.assertIsNone(read["effective_title"])
        async with self.engine.begin() as connection:
            values = (
                (
                    await connection.execute(
                        text(
                            f'SELECT value FROM "{self.schemas[0]}".catalog_variant_content_values WHERE variant_id=:id AND block_id=:block'
                        ),
                        {"id": variant["id"], "block": title},
                    )
                )
                .scalars()
                .all()
            )
            self.assertEqual(values, [])

    async def test_structure_ids_revisions_membership_and_pagination(self) -> None:
        """Редактор сохраняет ID; список считает Product; чужие позиции недоступны."""
        product, attr = await self.variable()
        path = "/products/" + product["id"]
        struct = self.structure(attr)
        # Match persistent IDs by selection, independently of SQL ordering.
        for row in struct["variants"]:
            row["variant_id"] = next(
                v["id"]
                for v in product["variants"]
                if v["selection"] == row["selection"]
            )
        struct["variants"].reverse()
        struct["variants"][0]["virtual"] = False
        await self.request(
            "PUT", path + "/structure", {"expected_revision": 1, "structure": struct}
        )
        updated = await self.request("GET", path + "?locale=en")
        self.assertEqual(
            {v["id"] for v in updated["variants"]},
            {v["id"] for v in product["variants"]},
        )
        await self.request(
            "PUT",
            path + "/structure",
            {"expected_revision": 1, "structure": struct},
            409,
        )
        simple = await self.create_product()
        await self.request(
            "GET", path + "/variants/" + simple["variant_id"] + "?locale=en", status=404
        )
        forged = copy.deepcopy(struct)
        forged["variants"][0]["variant_id"] = simple["variant_id"]
        await self.request(
            "PUT",
            path + "/structure",
            {"expected_revision": 2, "structure": forged},
            404,
        )
        await self.variable(attr)
        page = await self.request(
            "GET", "/products?locale=en&page_size=1&kind=variable"
        )
        self.assertEqual(page["total"], 2)
        self.assertEqual(len(page["items"]), 1)
        self.assertEqual(page["items"][0]["variant_count"], 2)
        second = await self.request(
            "GET", "/products?locale=en&page_size=1&page=2&kind=variable"
        )
        self.assertNotEqual(page["items"][0]["id"], second["items"][0]["id"])
        self.app.state.test_context = replace(
            self.context,
            principal=replace(self.context.principal, tenant_id=str(self.other)),
        )
        await self.request("GET", path + "?locale=en", status=404)
        await self.request(
            "GET", "/attributes/" + attr["id"] + "?locale=en", status=404
        )
        await self.request("POST", "/products/variable", {"structure": struct}, 404)

    async def test_invalid_axes_combinations_default_and_options_owner(self) -> None:
        """Сервер отклоняет неверную структуру до записи агрегата."""
        attr = await self.attribute()
        other = await self.attribute("size")
        valid = self.structure(attr)
        invalid = []
        single = copy.deepcopy(valid)
        single["variants"] = single["variants"][:1]
        invalid.append(single)
        duplicate = copy.deepcopy(valid)
        duplicate["variants"][1]["selection"] = duplicate["variants"][0]["selection"]
        invalid.append(duplicate)
        incomplete = copy.deepcopy(valid)
        incomplete["variants"][0]["selection"] = {}
        invalid.append(incomplete)
        default = copy.deepcopy(valid)
        default["default_selection"] = {attr["id"]: attr["options"][2]["id"]}
        invalid.append(default)
        foreign = copy.deepcopy(valid)
        foreign["axes"][0]["option_ids"][0] = other["options"][0]["id"]
        invalid.append(foreign)
        repeated = copy.deepcopy(valid)
        repeated["axes"].append(repeated["axes"][0])
        invalid.append(repeated)
        for structure in invalid:
            with self.subTest(structure=structure):
                await self.request(
                    "POST", "/products/variable", {"structure": structure}, 422
                )
        self.assertEqual((await self.request("GET", "/products?locale=en"))["total"], 0)
        await self.request("POST", "/products/variable", {"structure": valid}, 201)

    async def test_enum_usage_translation_reordering_and_removed_values(self) -> None:
        """Используемое разрешённое значение нельзя удалить; другие переводы сохраняются."""
        product, attr = await self.variable()
        path = "/attributes/" + attr["id"]
        options = [
            {"option_id": o["id"], "code": o["code"], "label": o["label"]}
            for o in attr["options"]
        ]
        await self.request(
            "PUT",
            path + "/options/en",
            {"expected_revision": 1, "options": options[:2]},
            409,
        )
        await self.request("DELETE", path + "?expected_revision=1", status=409)
        await self.request(
            "PUT", path + "/translations/ru", {"expected_revision": 1, "label": "Цвет"}
        )
        options.reverse()
        options[0]["label"] = "Зелёный"
        options[1]["label"] = "Синий"
        options[2]["label"] = "Красный"
        await self.request(
            "PUT", path + "/options/ru", {"expected_revision": 2, "options": options}
        )
        ru = await self.request("GET", path + "?locale=ru")
        en = await self.request("GET", path + "?locale=en")
        self.assertEqual(ru["options"][0]["id"], attr["options"][2]["id"])
        self.assertEqual(en["options"][0]["label"], "Green")
        self.assertEqual(ru["label"], "Цвет")
        self.assertEqual(en["label"], "color")
        renamed = copy.deepcopy(options)
        renamed[0]["code"] = "changed"
        await self.request(
            "PUT",
            path + "/options/ru",
            {"expected_revision": 3, "options": renamed},
            409,
        )
        await self.request(
            "DELETE", "/products/" + product["id"] + "?expected_revision=1", status=204
        )
        await self.request(
            "PUT",
            path + "/options/ru",
            {"expected_revision": 3, "options": options[:2]},
        )
        await self.request("DELETE", path + "?expected_revision=4", status=204)
        self.assertEqual(
            (await self.request("GET", "/attributes?locale=en"))["total"], 0
        )

    async def test_kind_transitions_and_content_protection(self) -> None:
        """Переходы и замена структуры защищают переводы всех локалей всех позиций."""
        product, attr = await self.variable()
        path = "/products/" + product["id"]
        variant = product["variants"][0]
        vpath = path + "/variants/" + variant["id"]
        await self.request(
            "PUT",
            vpath + "/content/ru",
            {"expected_revision": 1, "expected_schema_version": 1, "values": {}},
        )
        target = {
            "kind": "simple",
            "variant": {"variant_id": variant["id"], "selection": {}, "virtual": False},
        }
        await self.request(
            "PUT", path + "/kind", {"expected_revision": 2, "structure": target}, 422
        )
        struct = self.structure(attr)
        struct["variants"][0]["variant_id"] = next(
            v["id"] for v in product["variants"] if v["id"] != variant["id"]
        )
        struct["variants"][0]["selection"] = next(
            v["selection"] for v in product["variants"] if v["id"] != variant["id"]
        )
        struct["variants"][1]["selection"] = {attr["id"]: attr["options"][2]["id"]}
        struct["default_selection"] = None
        await self.request(
            "PUT",
            path + "/structure",
            {"expected_revision": 2, "structure": struct},
            409,
        )
        await self.request(
            "DELETE", vpath + "/content/ru?expected_revision=2", status=204
        )
        await self.request(
            "PUT", path + "/kind", {"expected_revision": 3, "structure": target}
        )
        simple = await self.request("GET", path + "?locale=en")
        self.assertEqual(simple["kind"], "simple")
        self.assertEqual(simple["variants"][0]["id"], variant["id"])
        self.assertEqual(simple["axes"], [])
        await self.request(
            "PUT",
            vpath + "/content/en",
            {"expected_revision": 4, "expected_schema_version": 1, "values": {}},
            422,
        )
        back = self.structure(attr)
        back["variants"][0]["variant_id"] = variant["id"]
        await self.request(
            "PUT", path + "/kind", {"expected_revision": 4, "structure": back}
        )
        await self.request(
            "PUT", path + "/kind", {"expected_revision": 5, "structure": back}, 422
        )
        self.assertEqual(
            len((await self.request("GET", path + "?locale=en"))["variants"]), 2
        )

    async def test_schema_change_checks_variant_translations_all_locales(self) -> None:
        """Смена схемы/типа не пропускает VARIANT-контент другой locale."""
        block = await self.request(
            "POST",
            "/content-blocks",
            {
                "code": "variant_note",
                "locale": "en",
                "label": "Note",
                "value_type": "text",
            },
            201,
        )
        typ = await self.request(
            "POST",
            "/product-types",
            {
                "code": "variants",
                "locale": "en",
                "label": "Variants",
                "blocks": [
                    {
                        "block_id": block["id"],
                        "scope": "VARIANT",
                        "required": False,
                        "position": 0,
                    }
                ],
            },
            201,
        )
        attr = await self.attribute()
        p = await self.request(
            "POST",
            "/products/variable",
            {"product_type_id": typ["id"], "structure": self.structure(attr)},
            201,
        )
        product = await self.request("GET", "/products/" + p["id"] + "?locale=en")
        vid = product["variants"][0]["id"]
        await self.request(
            "PUT",
            "/products/" + p["id"] + "/variants/" + vid + "/content/ru",
            {
                "expected_revision": 1,
                "expected_schema_version": 1,
                "values": {block["id"]: "Сохранить"},
            },
        )
        await self.request(
            "PUT",
            "/product-types/" + typ["id"] + "/schema",
            {"expected_revision": 1, "expected_schema_version": 1, "blocks": []},
            422,
        )
        default = next(
            t
            for t in (await self.request("GET", "/product-types?locale=en"))["items"]
            if t["code"] == "default"
        )
        await self.request(
            "PUT",
            "/products/" + p["id"] + "/type",
            {"expected_revision": 2, "product_type_id": default["id"]},
            422,
        )
        self.assertEqual(
            (
                await self.request(
                    "GET", "/products/" + p["id"] + "/variants/" + vid + "?locale=ru"
                )
            )["content"][block["id"]],
            "Сохранить",
        )

    async def test_upgrade_preserves_simple_and_downgrade_rejects_variable(
        self,
    ) -> None:
        """Миграция сохраняет ID, контент и ревизии; downgrade не уничтожает VARIABLE."""
        async with self.engine.begin() as connection:
            await TenantMigrator().downgrade(
                connection, self.schemas[0], "0017_catalog_simple"
            )
        simple = {"id": str(uuid4()), "variant_id": str(uuid4())}
        path = "/products/" + simple["id"]
        schema = self.schemas[0]
        # Seed the previous schema directly: current application requires head.
        async with self.engine.begin() as connection:
            await connection.execute(
                text(
                    f"INSERT INTO \"{schema}\".catalog_products(id,kind,product_type_id,revision,created_by,updated_by) VALUES (:id,'simple','c0000000-0000-4000-8000-000000000001',2,:actor,:actor)"
                ),
                {"id": simple["id"], "actor": str(self.actor)},
            )
            await connection.execute(
                text(
                    f'INSERT INTO "{schema}".catalog_variants(id,product_id,virtual,downloadable) VALUES (:vid,:pid,true,false)'
                ),
                {"vid": simple["variant_id"], "pid": simple["id"]},
            )
            await connection.execute(
                text(
                    f"INSERT INTO \"{schema}\".catalog_product_translations(product_id,locale) VALUES (:id,'en')"
                ),
                {"id": simple["id"]},
            )
            await connection.execute(
                text(
                    f"INSERT INTO \"{schema}\".catalog_product_content_values(product_id,locale,block_id,value) VALUES (:id,'en','c0000000-0000-4000-8000-000000000002','Preserved')"
                ),
                {"id": simple["id"]},
            )
            await TenantMigrator().upgrade(connection, schema)
        read = await self.request("GET", path + "?locale=en")
        self.assertEqual(read["revision"], 2)
        self.assertEqual(read["title"], "Preserved")
        self.assertEqual(read["variants"][0]["id"], simple["variant_id"])
        self.assertTrue(read["variants"][0]["virtual"])
        product, _ = await self.variable()
        with self.assertRaises(RuntimeError):
            async with self.engine.begin() as connection:
                await TenantMigrator().downgrade(
                    connection, self.schemas[0], "0017_catalog_simple"
                )
        self.assertEqual((await self.request("GET", "/products?locale=en"))["total"], 2)
        await self.request(
            "DELETE", "/products/" + product["id"] + "?expected_revision=1", status=204
        )
        async with self.engine.begin() as connection:
            await TenantMigrator().downgrade(
                connection, self.schemas[0], "0017_catalog_simple"
            )
        async with self.engine.begin() as connection:
            value = await connection.scalar(
                text(
                    f'SELECT value FROM "{schema}".catalog_product_content_values WHERE product_id=:id'
                ),
                {"id": simple["id"]},
            )
            self.assertEqual(value, "Preserved")
            await TenantMigrator().upgrade(connection, schema)

    async def test_sql_constraints_reject_foreign_axis_option(self) -> None:
        """Составной FK запрещает option вне разрешённых значений оси."""
        product, attr = await self.variable()
        other = await self.attribute("size")
        schema = self.schemas[0]
        variant = product["variants"][0]
        async with self.engine.begin() as connection:
            with self.assertRaises(IntegrityError):
                async with connection.begin_nested():
                    await connection.execute(
                        text(
                            f'UPDATE "{schema}".catalog_variant_selections SET option_id=:option WHERE variant_id=:variant'
                        ),
                        {"option": other["options"][0]["id"], "variant": variant["id"]},
                    )
        self.assertEqual(
            len(
                (
                    await self.request(
                        "GET", "/products/" + product["id"] + "?locale=en"
                    )
                )["variants"]
            ),
            2,
        )

    async def test_sql_constraints_reject_selection_for_foreign_variant(self) -> None:
        """Составной FK запрещает selection для позиции другого Product."""
        simple = await self.request("POST", "/products/simple", {}, 201)
        product, attr = await self.variable()
        schema = self.schemas[0]
        with self.assertRaises(IntegrityError):
            async with self.engine.begin() as connection:
                await connection.execute(
                    text(
                        f'INSERT INTO "{schema}".catalog_variant_selections(variant_id,attribute_id,product_id,option_id) VALUES (:variant,:attribute,:target,:option)'
                    ),
                    {
                        "variant": simple["variant_id"],
                        "attribute": attr["id"],
                        "target": product["id"],
                        "option": attr["options"][2]["id"],
                    },
                )
        restored = await self.request("GET", "/products/" + simple["id"] + "?locale=en")
        self.assertEqual(
            [v["id"] for v in restored["variants"]], [simple["variant_id"]]
        )
