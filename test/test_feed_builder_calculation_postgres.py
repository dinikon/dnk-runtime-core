"""Формулы FeedBuilder через реальные HTTP, Catalog и tenant PostgreSQL."""

import copy
import os
import unittest
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal
from unittest.mock import Mock, AsyncMock, patch
from uuid import UUID, uuid4
from sqlalchemy import event
from sqlalchemy.engine import Connection
from sqlalchemy.engine.interfaces import ExecutionContext
from test import test_feed_builder_crud_postgres as crud_support
from test.test_feed_builder_calculation import calculation_field
from test.test_feed_builder_domain import NOW
from test.catalog_support import initialize_catalog
from src.modules.catalog.presentation.router import router as catalog_router
from src.modules.catalog.application.catalog_item.port.calculation_reader import (
    CatalogCalculationReference,
)
from src.modules.catalog.infrastructure.catalog_item.persistence.calculation_reader import (
    SqlAlchemyCatalogCalculationReader,
)
from src.modules.feed_builder.application.feed.schema_document import field_document
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.feed_builder.domain.feed.aggregate import Feed
from src.modules.identity.domain.auth.principal import Principal
from src.modules.identity.domain.auth.request_context import RequestContext


@unittest.skipUnless(
    os.environ.get("TEST_POSTGRES_URL"), "Requires disposable PostgreSQL"
)
class FeedCalculationPostgresTests(unittest.IsolatedAsyncioTestCase):
    """Проверяет законченный сценарий без подмены цен клиентскими данными."""

    refresh_csrf = crud_support.FeedCrudPostgresTests.refresh_csrf
    scoped_session = crud_support.FeedCrudPostgresTests.scoped_session
    create = crud_support.FeedCrudPostgresTests.create
    asyncTearDown = crud_support.FeedCrudPostgresTests.asyncTearDown

    async def asyncSetUp(self) -> None:
        """Создаёт изолированные tenant и Catalog с действующими owner-правилами."""
        await crud_support.FeedCrudPostgresTests.asyncSetUp(self)
        self.app.include_router(catalog_router, prefix="/api/console")
        for tenant in (self.tenant, self.other):
            async with self.scoped_session(tenant) as session:
                await initialize_catalog(session, tenant, EntityIdVO(self.actor))
        self.app.state.clock = Mock(now=lambda: NOW)
        self.feed = await self.create()
        self.field = field_document(calculation_field())
        self.field["type_definition"]["currency"] = None
        self.catalog = "/api/console/catalog/items"

    async def item(
        self,
        kind: str = "simple",
        *,
        parent: str | None = None,
        sale: str | None = "900",
    ) -> str:
        """Создаёт SIMPLE/VARIABLE/VARIANT через действующий Catalog API."""
        data: dict[str, object] = {"sku": f"PRICE-{uuid4().hex[:10]}"}
        if parent is None:
            data["kind"] = kind
        if kind != "variable":
            data["price_specification"] = {
                "regular_price": "1000",
                "sale_price": sale,
                "date_on_sale_from": (
                    (NOW - timedelta(days=1)).isoformat() if sale is not None else None
                ),
                "date_on_sale_to": (
                    (NOW + timedelta(days=1)).isoformat() if sale is not None else None
                ),
            }
        response = await self.client.post(
            self.catalog + (f"/{parent}/variants" if parent else ""),
            json=data,
            headers=self.headers,
        )
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()["id"]

    async def preview(
        self,
        item_id: str,
        *,
        variant_id: str | None = None,
        expected: int = 1,
        field: dict | None = None,
        status: int = 200,
    ) -> dict:
        """Передаёт только определение и идентификаторы, проверяя HTTP-статус."""
        definition = field or self.field
        response = await self.client.post(
            f"{self.base}/{self.feed['id']}/calculation-preview",
            headers=self.headers,
            json={
                "expected_version": expected,
                "field_id": definition["id"],
                "catalog_item_id": item_id,
                "catalog_variant_id": variant_id,
                "definition_override": definition,
            },
        )
        self.assertEqual(response.status_code, status, response.text)
        return response.json()

    async def test_preview_unsaved_save_reopen_and_read_only_version(self) -> None:
        """Проверяет несохранённый AST, round-trip и неизменность Feed после расчёта."""
        item = await self.item()
        with patch.object(
            Feed,
            "restore",
            side_effect=AssertionError("Preview must not restore aggregate"),
        ):
            result = await self.preview(item)
        self.assertEqual(result["resolved_value"], {"amount": "990.00"})
        self.assertEqual(
            result["selected_rule_id"],
            self.field["type_definition"]["value"]["calculation"]["rules"][0]["id"],
        )
        self.assertFalse(result["used_default"])
        self.assertEqual(result["source_revision"], 1)
        self.assertEqual(result["catalog_item_id"], item)
        self.assertEqual(result["validation_status"], "VALID")
        self.assertIsNotNone(result["valid_until"])
        before = (await self.client.get(f"{self.base}/{self.feed['id']}")).json()
        self.assertEqual(before["version"], 1)
        self.assertEqual(before["schema"]["root"]["fields"], [])
        response = await self.client.put(
            f"{self.base}/{self.feed['id']}/schema/draft",
            headers=self.headers,
            json={
                "expected_version": 1,
                "definition": {
                    "schema_format_version": 1,
                    "root": {
                        "key": "publication",
                        "kind": "object",
                        "fields": [self.field],
                    },
                },
            },
        )
        self.assertEqual(response.status_code, 200, response.text)
        saved = response.json()
        self.assertEqual(saved["version"], 2)
        self.assertEqual(saved["definition"]["root"]["fields"][0], self.field)
        await self.preview(item, status=409)
        result = await self.preview(item, expected=2)
        self.assertEqual(result["version"], 2)
        self.assertEqual(
            (await self.client.get(f"{self.base}/{self.feed['id']}")).json()["version"],
            2,
        )

        changed = await self.client.patch(
            f"{self.catalog}/{item}",
            headers=self.headers,
            json={
                "price_specification": {"regular_price": "1000", "sale_price": "700"}
            },
        )
        self.assertEqual(changed.status_code, 200, changed.text)
        fresh = await self.preview(item, expected=2)
        self.assertEqual(fresh["resolved_value"], {"amount": "770.00"})
        self.assertEqual(fresh["source_revision"], 1)
        # Catalog revision пассивен: новое значение читается заново без кеша по revision.
        async with self.scoped_session() as session:
            from sqlalchemy import update
            from src.modules.catalog.infrastructure.persistence.models.catalog_item import (
                CatalogItemModel,
            )

            await session.execute(
                update(CatalogItemModel)
                .where(CatalogItemModel.id == UUID(item))
                .values(revision=17)
            )
        self.assertEqual((await self.preview(item, expected=2))["source_revision"], 17)
        self.assertEqual(fresh["version"], 2)

    async def test_variant_pair_and_else_are_selected_explicitly(self) -> None:
        """Не считает контейнер, чужой вариант или VARIANT в роли корня."""
        root = await self.item("variable")
        child = await self.item("variant", parent=root, sale=None)
        unrelated = await self.item("variable")
        await self.preview(root, status=404)
        await self.preview(child, status=404)
        await self.preview(unrelated, variant_id=child, status=404)
        result = await self.preview(root, variant_id=child)
        self.assertEqual(result["resolved_value"], {"amount": "1150.00"})
        self.assertEqual(result["selected_product_id"], child)
        self.assertEqual(result["product_kind"], "variant")
        self.assertTrue(result["used_default"])
        self.assertIsNone(result["selected_rule_id"])
        self.assertIn({"id": "price.sale", "value": None}, result["parameters"])

    async def test_semantic_runtime_and_request_errors_are_distinct(self) -> None:
        """Тип коллекции отклоняется в арифметике, ошибки исполнения не становятся ELSE."""
        item = await self.item(sale=None)
        invalid = copy.deepcopy(self.field)
        invalid["type_definition"]["value"]["calculation"]["rules"][0]["expression"] = {
            "kind": "parameter",
            "parameter": "product.category_ids",
        }
        result = await self.preview(str(uuid4()), field=invalid, status=422)
        self.assertEqual(result["detail"]["code"], "INVALID_EXPRESSION_TYPE")
        response = await self.client.put(
            f"{self.base}/{self.feed['id']}/schema/draft",
            headers=self.headers,
            json={
                "expected_version": 1,
                "definition": {
                    "schema_format_version": 1,
                    "root": {
                        "key": "publication",
                        "kind": "object",
                        "fields": [invalid],
                    },
                },
            },
        )
        self.assertEqual(response.status_code, 422, response.text)
        self.assertEqual(response.json()["detail"]["code"], "INVALID_EXPRESSION_TYPE")
        self.assertEqual(response.json()["detail"]["field_id"], self.field["id"])
        invalid = copy.deepcopy(self.field)
        calc = invalid["type_definition"]["value"]["calculation"]
        calc["rules"][0]["condition"] = {
            "kind": "comparison",
            "operator": "GT",
            "left": {"kind": "parameter", "parameter": "price.sale"},
            "right": {"kind": "decimal", "value": "0"},
        }
        result = await self.preview(item, field=invalid)
        self.assertEqual(result["validation_status"], "INVALID")
        self.assertIsNone(result["resolved_value"])
        self.assertFalse(result["used_default"])
        self.assertEqual(result["issues"][0]["code"], "CALCULATION_PARAMETER_MISSING")
        self.assertEqual(result["issues"][0]["field_id"], invalid["id"])
        body = {
            "expected_version": 1,
            "field_id": self.field["id"],
            "catalog_item_id": item,
            "as_of": NOW.isoformat(),
            "prices": {"regular": "1"},
        }
        response = await self.client.post(
            f"{self.base}/{self.feed['id']}/calculation-preview",
            headers=self.headers,
            json=body,
        )
        self.assertEqual(response.status_code, 422)
        payload = {
            "expected_version": 1,
            "field_id": self.field["id"],
            "catalog_item_id": item,
            "definition_override": self.field,
        }
        response = await self.client.post(
            f"{self.base}/{self.feed['id']}/calculation-preview", json=payload
        )
        self.assertEqual(response.status_code, 403)
        endpoint = f"{self.base}/{self.feed['id']}/calculation-preview"
        response = await self.client.post(
            endpoint,
            headers={**self.headers, "Content-Type": "application/json"},
            content='{"padding":"' + "x" * (1024 * 1024) + '"}',
        )
        self.assertEqual(response.status_code, 413)
        response = await self.client.post(
            endpoint,
            headers={**self.headers, "Content-Type": "application/json"},
            content="[" * 161 + "0" + "]" * 161,
        )
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()["detail"]["code"], "SCHEMA_LIMIT_EXCEEDED")
        from src.modules.feed_builder.presentation.feed.depends import (
            get_calculation_products,
        )
        from src.modules.feed_builder.application.feed.port.calculation_product import (
            CalculationDependencyUnavailableError,
        )

        self.app.dependency_overrides[get_calculation_products] = lambda: Mock(
            read=AsyncMock(
                side_effect=CalculationDependencyUnavailableError("Catalog недоступен")
            )
        )
        await self.preview(item, status=503)
        self.app.dependency_overrides.pop(get_calculation_products)

    async def test_metadata_permissions_archive_and_tenant_isolation(self) -> None:
        """Защищает входные параметры и trace правами и tenant-привязкой."""
        item = await self.item()
        parameters = (
            await self.client.get("/api/console/feed-builder/calculation-parameters")
        ).json()
        self.assertEqual(
            {p["id"] for p in parameters["items"]},
            {
                "price.regular",
                "price.sale",
                "price.effective",
                "product.id",
                "product.sku",
                "price.purchase",
                "product.category_ids",
            },
        )
        operations = (
            await self.client.get("/api/console/feed-builder/calculation-operations")
        ).json()
        self.assertEqual(operations["precision"], 40)
        self.assertEqual(operations["max_collection_items"], 500)
        self.assertEqual(operations["engine_version"], "1")

        class DenyCatalog:
            """Отклоняет чтение источника независимо от прав Feed."""

            async def can(self, **kwargs: object) -> bool:
                """Проверяет отдельное право на выбранную позицию."""
                return kwargs["action"] != "catalog.item.read"

        self.app.state.authorization_service = DenyCatalog()
        await self.preview(item, status=403)
        del self.app.state.authorization_service
        context = self.app.state.test_context
        self.app.state.test_context = RequestContext(
            Principal(str(self.actor), str(self.other.uuid), "feed-test", ("member",)),
            None,
            None,
            None,
        )
        await self.refresh_csrf()
        await self.preview(item, status=404)
        original_feed = self.feed
        self.feed = await self.create("other-tenant-preview")
        await self.preview(item, status=404)
        self.feed = original_feed
        self.app.state.test_context = context
        await self.refresh_csrf()
        response = await self.client.delete(
            f"{self.base}/{self.feed['id']}?expected_version=1", headers=self.headers
        )
        self.assertEqual(response.status_code, 204, response.text)
        await self.preview(item, expected=2, status=409)

    async def test_owner_reader_batches_selected_positions_and_sale_boundaries(
        self,
    ) -> None:
        """Один SELECT читает только выбранные ID и использует полуоткрытый период акции."""
        item = await self.item(sale="0")
        queries: list[str] = []

        def capture(
            connection: Connection,
            cursor: object,
            statement: str,
            parameters: object,
            context: ExecutionContext,
            executemany: bool,
        ) -> None:
            """Считает SQL чтения источника внутри пакетного вызова."""
            if "SELECT" in statement and "catalog_item" in statement:
                queries.append(statement)

        event.listen(self.engine.sync_engine, "before_cursor_execute", capture)
        try:
            async with self.scoped_session() as session:
                reader = SqlAlchemyCatalogCalculationReader(session)
                ref = CatalogCalculationReference(UUID(item), None)
                rows = await reader.read_many((ref, ref), NOW)
                self.assertEqual(len(queries), 1)
                self.assertEqual(rows[0].sale, Decimal(0))
                self.assertEqual(rows[0].effective, Decimal(0))
                self.assertEqual(rows[0].valid_until, NOW + timedelta(days=1))
                self.assertEqual(rows[0].revision, 1)
                self.assertEqual(
                    (await reader.read_many((ref,), NOW + timedelta(days=1)))[0].sale,
                    None,
                )
                self.assertEqual(
                    (await reader.read_many((ref,), NOW - timedelta(days=1)))[0].sale,
                    Decimal(0),
                )
                self.assertEqual(
                    (await reader.read_many((ref,), NOW - timedelta(days=2)))[
                        0
                    ].valid_until,
                    NOW - timedelta(days=1),
                )
        finally:
            event.remove(self.engine.sync_engine, "before_cursor_execute", capture)
        same = await self.item(sale="1000")
        async with self.scoped_session() as session:
            snapshot = (
                await SqlAlchemyCatalogCalculationReader(session).read_many(
                    (CatalogCalculationReference(UUID(same)),), NOW
                )
            )[0]
            self.assertIsNone(snapshot.sale)
            self.assertEqual(snapshot.effective, Decimal("1000"))
