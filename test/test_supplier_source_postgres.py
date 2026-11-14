from src.modules.crm.presentation.counterparty_reference.router import (
    router as counterparty_router,
)
from src.modules.crm.presentation.contact.router import router as contact_router
from src.modules.crm.infrastructure.persistence.models.contact import ContactModel

"""Полный HTTP-путь источников на PostgreSQL, миграции и гонки ссылок CRM."""

import asyncio
from dataclasses import replace
from datetime import timedelta
import os
import unittest
from unittest.mock import patch, Mock
from uuid import UUID, uuid4
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, insert, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool
from sqlalchemy.schema import CreateSchema, DropSchema
from src.config import dnk_config
from src.modules.identity.domain.auth.principal import Principal
from src.modules.identity.domain.auth.request_context import RequestContext
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.tenancy.application.tenant.tenant_schema_naming import (
    TenantSchemaNaming,
)
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_connection import (
    bind_tenant_schema,
)
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_migrations import (
    TenantMigrator,
)
from src.modules.supplier_sourcing.presentation.supplier_source.router import (
    router as source_router,
)
from src.modules.supplier_sourcing.infrastructure.persistence.models.supplier_source import (
    SupplierSourceModel,
)
from src.modules.supplier_sourcing.infrastructure.persistence.models.supplier_source_fulfillment_mode import (
    SupplierSourceFulfillmentModeModel,
)
from src.modules.supplier_sourcing.infrastructure.supplier_source.persistence.repository import (
    SqlAlchemySupplierSourceRepository,
)
from src.modules.supplier_sourcing.domain.supplier_source.value_object.identifier import (
    SupplierSourceIdVO,
)
from src.modules.crm.infrastructure.persistence.models.company import CompanyModel
from src.modules.crm.infrastructure.counterparty_reference.repository import (
    SqlAlchemyCounterpartyReferenceRepository,
)
from src.modules.crm.application.counterparty_reference.dto import CounterpartyModelKey
from test.crm_company_support import company_app


@unittest.skipUnless(
    os.environ.get("TEST_POSTGRES_URL"), "Требуется одноразовая PostgreSQL БД."
)
class SupplierSourcePostgresTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.engine = create_async_engine(
            os.environ["TEST_POSTGRES_URL"], poolclass=NullPool
        )
        self.addAsyncCleanup(self.engine.dispose)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        self.naming = TenantSchemaNaming(dnk_config.SCHEMA_PREFIX)
        self.tenant, self.other = EntityIdVO(uuid4()), EntityIdVO(uuid4())
        self.schemas = [
            self.naming.schema_name(value) for value in (self.tenant, self.other)
        ]
        self.addAsyncCleanup(self.drop_schemas)
        async with self.engine.begin() as connection:
            for schema in self.schemas:
                await connection.execute(CreateSchema(schema))
                await TenantMigrator().upgrade(connection, schema)
        self.context = RequestContext(
            Principal(str(uuid4()), str(self.tenant), "session", ("member",)),
            None,
            None,
            None,
        )
        self.app = company_app(self.sessions, self.context, scoped_connection=True)
        self.app.include_router(source_router, prefix="/api/console")
        self.app.include_router(counterparty_router, prefix="/api/console")
        self.app.include_router(contact_router, prefix="/api/console")
        scheme = "http" if dnk_config.AUTH.allow_insecure_http else "https"
        origin = f"{scheme}://tenant.example"
        self.client = AsyncClient(
            transport=ASGITransport(app=self.app, raise_app_exceptions=False),
            base_url=origin,
        )
        self.addAsyncCleanup(self.client.aclose)
        token = (await self.client.get("/csrf")).json()["csrf_token"]
        self.headers = {"Origin": origin, "X-CSRF-Token": token}
        self.base = "/api/console/supplier-sourcing/sources"
        response = await self.client.post(
            "/api/console/crm/companies",
            headers=self.headers,
            json={"legal_name": "Supplier ACME"},
        )
        self.assertEqual(response.status_code, 201, response.text)
        self.company = response.json()
        self.payload = dict(
            supplier_model_key="crm.company",
            supplier_id=self.company["id"],
            name=" Source A ",
            external_warehouse_code=" 000Code-a_% ",
            fulfillment_modes=["DROPSHIP", "PURCHASE_TO_WAREHOUSE"],
            default_lead_time_seconds=0,
            stock_update_policy=dict(
                ttl_seconds=3600,
                stale_behavior="MARK_UNKNOWN",
                missing_sku_behavior="MARK_UNKNOWN",
            ),
        )

    async def drop_schemas(self) -> None:
        async with self.engine.begin() as connection:
            for schema in self.schemas:
                await connection.execute(
                    DropSchema(schema, cascade=True, if_exists=True)
                )

    async def create_source(self, **changes: object) -> dict:
        response = await self.client.post(
            self.base, headers=self.headers, json={**self.payload, **changes}
        )
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()

    async def test_create_list_card_search_filter_page_and_live_company_name(
        self,
    ) -> None:
        first = await self.create_source()
        await self.create_source(name="Source B")
        self.assertEqual(
            (
                first["name"],
                first["external_warehouse_code"],
                first["is_active"],
                first["supplier_name"],
            ),
            ("Source A", "000Code-a_%", True, "Supplier ACME"),
        )
        self.assertEqual(
            (await self.client.get(f"{self.base}/{first['id']}")).json(), first
        )
        response = await self.client.get(
            self.base,
            params={
                "search": "_%",
                "fulfillment_mode": "DROPSHIP",
                "supplier_model_key": "crm.company",
                "supplier_id": self.company["id"],
                "limit": 1,
                "offset": 1,
            },
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(
            (response.json()["total"], response.json()["items"][0]["name"]),
            (2, "Source B"),
        )
        renamed = await self.client.patch(
            f"/api/console/crm/companies/{self.company['id']}",
            headers=self.headers,
            json={"legal_name": "Renamed"},
        )
        self.assertEqual(renamed.status_code, 200, renamed.text)
        self.assertEqual(
            (await self.client.get(self.base)).json()["items"][0]["supplier_name"],
            "Renamed",
        )

    async def test_put_patch_preserve_identity_modes_zero_false_and_clear_code(
        self,
    ) -> None:
        source = await self.create_source()
        url = f"{self.base}/{source['id']}"
        response = await self.client.patch(
            url,
            headers=self.headers,
            json={
                "default_lead_time_seconds": 10,
                "is_active": False,
                "external_warehouse_code": None,
            },
        )
        self.assertEqual(response.status_code, 200, response.text)
        value = response.json()
        self.assertEqual(
            (
                value["supplier_id"],
                value["fulfillment_modes"],
                value["is_active"],
                value["external_warehouse_code"],
            ),
            (source["supplier_id"], source["fulfillment_modes"], False, None),
        )
        self.assertEqual(
            (await self.client.get(self.base, params={"is_active": False})).json()[
                "total"
            ],
            1,
        )
        policy = dict(
            ttl_seconds=900,
            stale_behavior="BLOCK_AUTOMATIC_SALE",
            missing_sku_behavior="KEEP_LAST",
        )
        response = await self.client.put(
            url,
            headers=self.headers,
            json=dict(
                name="New",
                external_warehouse_code="000NEW",
                fulfillment_modes=["PURCHASE_TO_WAREHOUSE"],
                default_lead_time_seconds=0,
                is_active=True,
                stock_update_policy=policy,
            ),
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["stock_update_policy"], policy)
        self.assertEqual(
            (
                await self.client.get(
                    self.base, params={"fulfillment_mode": "DROPSHIP"}
                )
            ).json()["total"],
            0,
        )
        self.assertEqual(
            (
                await self.client.get(
                    self.base, params={"fulfillment_mode": "PURCHASE_TO_WAREHOUSE"}
                )
            ).json()["total"],
            1,
        )
        self.assertEqual((await self.client.get(url)).json(), response.json())

    async def test_validation_csrf_and_no_partial_changes(self) -> None:
        source = await self.create_source()
        url = f"{self.base}/{source['id']}"
        self.assertEqual(
            (await self.client.patch(url, json={"name": "No CSRF"})).status_code, 403
        )
        for payload in (
            {},
            {"supplier_id": str(uuid4())},
            {"name": None},
            {"fulfillment_modes": []},
            {"is_active": 0},
            {"stock_update_policy": {"ttl_seconds": 900}},
            {"default_lead_time_seconds": 0.5},
            {"default_lead_time_seconds": 86400000000000},
            {
                "stock_update_policy": dict(
                    ttl_seconds=0,
                    stale_behavior="MARK_UNKNOWN",
                    missing_sku_behavior="KEEP_LAST",
                )
            },
            {"name": "Changed", "fulfillment_modes": []},
        ):
            with self.subTest(payload=payload):
                response = await self.client.patch(
                    url, headers=self.headers, json=payload
                )
                self.assertEqual(response.status_code, 422, response.text)
                self.assertEqual((await self.client.get(url)).json(), source)
        self.assertEqual(
            (
                await self.client.get(self.base, params={"fulfillment_mode": "WRONG"})
            ).status_code,
            422,
        )
        self.assertEqual(
            (await self.client.get(self.base, params={"limit": 101})).status_code, 422
        )

    async def test_tenant_isolation_supplier_validation_and_company_search(
        self,
    ) -> None:
        source = await self.create_source()
        page = (
            await self.client.get(
                "/api/console/crm/counterparty-references",
                params={"model_key": "crm.company", "search": "acme"},
            )
        ).json()
        self.assertEqual(
            (page["total"], page["items"][0]["id"]), (1, self.company["id"])
        )
        self.app.state.test_context = replace(
            self.context,
            principal=replace(self.context.principal, tenant_id=str(self.other)),
        )
        self.assertEqual((await self.client.get(self.base)).json()["total"], 0)
        self.assertEqual(
            (
                await self.client.get(
                    "/api/console/crm/counterparty-references",
                    params={"model_key": "crm.company"},
                )
            ).json()["total"],
            0,
        )
        self.assertEqual(
            (await self.client.get(f"{self.base}/{source['id']}")).status_code, 404
        )
        self.assertEqual(
            (
                await self.client.patch(
                    f"{self.base}/{source['id']}",
                    headers=self.headers,
                    json={"name": "Other"},
                )
            ).status_code,
            404,
        )
        response = await self.client.post(
            self.base, headers=self.headers, json=self.payload
        )
        self.assertEqual(response.status_code, 404, response.text)
        self.assertEqual((await self.client.get(self.base)).json()["total"], 0)

    async def test_used_inactive_source_blocks_company_deletion_without_fk(
        self,
    ) -> None:
        source = await self.create_source()
        response = await self.client.patch(
            f"{self.base}/{source['id']}",
            headers=self.headers,
            json={"is_active": False},
        )
        self.assertEqual(response.status_code, 200, response.text)
        with patch(
            "src.modules.crm.infrastructure.contact_point.adapter.ContactPointsAdapter.remove",
            side_effect=AssertionError("Contact side effects must not run"),
        ):
            response = await self.client.delete(
                f"/api/console/crm/companies/{self.company['id']}", headers=self.headers
            )
        self.assertEqual(response.status_code, 409, response.text)
        # The link has deliberately no FK; application deletion remains protected above.
        async with self.engine.connect() as connection:
            await bind_tenant_schema(connection, self.tenant.uuid, self.naming)
            result = await connection.execute(
                delete(CompanyModel)
                .where(CompanyModel.id == UUID(self.company["id"]))
                .returning(CompanyModel.id)
            )
            self.assertEqual(result.scalar_one(), UUID(self.company["id"]))
            await connection.rollback()
        self.assertEqual((await self.client.get(self.base)).json()["total"], 1)

    async def test_root_and_modes_rollback_together(self) -> None:
        with patch.object(
            SqlAlchemySupplierSourceRepository,
            "_write_modes",
            side_effect=RuntimeError("mode write failed"),
        ):
            response = await self.client.post(
                self.base, headers=self.headers, json=self.payload
            )
        self.assertEqual(response.status_code, 500)
        self.assertEqual((await self.client.get(self.base)).json()["total"], 0)
        source = await self.create_source()
        with patch.object(
            SqlAlchemySupplierSourceRepository,
            "_write_modes",
            side_effect=RuntimeError("mode write failed"),
        ):
            response = await self.client.patch(
                f"{self.base}/{source['id']}",
                headers=self.headers,
                json={"name": "Changed", "fulfillment_modes": ["DROPSHIP"]},
            )
        self.assertEqual(response.status_code, 500)
        self.assertEqual(
            (await self.client.get(f"{self.base}/{source['id']}")).json(), source
        )

    async def test_company_lock_serializes_creation_with_deletion(self) -> None:
        source = await self.create_source()
        # Temporarily remove the first source; reuse its valid aggregate to exercise a fresh reference race.
        async with self.engine.begin() as connection:
            await bind_tenant_schema(connection, self.tenant.uuid, self.naming)
            async with async_sessionmaker(
                connection, expire_on_commit=False
            )() as session:
                aggregate = await SqlAlchemySupplierSourceRepository(
                    session
                ).get_for_update(SupplierSourceIdVO(UUID(source["id"])))
            await connection.execute(
                delete(SupplierSourceModel).where(
                    SupplierSourceModel.id == UUID(source["id"])
                )
            )
        async with self.engine.connect() as connection:
            await bind_tenant_schema(connection, self.tenant.uuid, self.naming)
            async with async_sessionmaker(
                connection, expire_on_commit=False
            )() as session:
                self.assertIsNotNone(
                    await SqlAlchemyCounterpartyReferenceRepository(session).get(
                        CounterpartyModelKey.COMPANY,
                        UUID(self.company["id"]),
                        lock=True,
                    )
                )
                task = asyncio.create_task(
                    self.client.delete(
                        f"/api/console/crm/companies/{self.company['id']}",
                        headers=self.headers,
                    )
                )
                try:
                    await asyncio.sleep(0.1)
                    self.assertFalse(
                        task.done(), "Удаление должно ждать FOR KEY SHARE компании."
                    )
                    await SqlAlchemySupplierSourceRepository(session).add(aggregate)
                    await session.commit()
                    response = await asyncio.wait_for(task, 5)
                    self.assertEqual(response.status_code, 409, response.text)
                finally:
                    if not task.done():
                        task.cancel()
                        await asyncio.gather(task, return_exceptions=True)

    async def test_protective_constraints_and_migration_round_trip(self) -> None:
        source = await self.create_source()
        for values in (
            {"stock_ttl_seconds": 0},
            {"default_lead_time_seconds": -1},
            {"stale_behavior": "OTHER"},
        ):
            with self.assertRaises(IntegrityError):
                async with self.engine.begin() as connection:
                    await bind_tenant_schema(connection, self.tenant.uuid, self.naming)
                    from sqlalchemy import update

                    await connection.execute(
                        update(SupplierSourceModel)
                        .where(SupplierSourceModel.id == UUID(source["id"]))
                        .values(**values)
                    )
        with self.assertRaises(IntegrityError):
            async with self.engine.begin() as connection:
                await bind_tenant_schema(connection, self.tenant.uuid, self.naming)
                await connection.execute(
                    insert(SupplierSourceFulfillmentModeModel).values(
                        supplier_source_id=UUID(source["id"]), mode="WRONG"
                    )
                )
        async with self.engine.begin() as connection:
            await TenantMigrator().downgrade(
                connection, self.schemas[0], "0023_inventory_stock_serials"
            )
            self.assertIsNone(
                await connection.scalar(
                    text("SELECT to_regclass(:name)"),
                    {"name": f"{self.schemas[0]}.supplier_sources"},
                )
            )
            await TenantMigrator().upgrade(connection, self.schemas[0])
        self.assertEqual((await self.client.get(self.base)).json()["total"], 0)
        self.assertEqual(
            (
                await self.client.get(
                    "/api/console/crm/counterparty-references",
                    params={"model_key": "crm.company"},
                )
            ).json()["total"],
            1,
        )

    async def test_concurrent_patch_and_fresh_rehydration(self) -> None:
        """Ожидание блокировки не теряет чужие поля и не использует старую identity map."""
        source = await self.create_source()
        url = f"{self.base}/{source['id']}"
        async with self.engine.connect() as connection:
            await bind_tenant_schema(connection, self.tenant.uuid, self.naming)
            async with async_sessionmaker(
                connection, expire_on_commit=False
            )() as session:
                retained = (
                    await session.scalars(
                        select(SupplierSourceModel).where(
                            SupplierSourceModel.id == UUID(source["id"])
                        )
                    )
                ).one()
                response = await self.client.patch(
                    url, headers=self.headers, json={"name": "Fresh name"}
                )
                self.assertEqual(response.status_code, 200, response.text)
                self.assertEqual(retained.name, "Source A")
                refreshed = await SqlAlchemySupplierSourceRepository(
                    session
                ).get_for_update(SupplierSourceIdVO(UUID(source["id"])))
                self.assertEqual(refreshed.name.value, "Fresh name")
                task = asyncio.create_task(
                    self.client.patch(
                        url,
                        headers=self.headers,
                        json={"default_lead_time_seconds": 42},
                    )
                )
                try:
                    await asyncio.sleep(0.1)
                    self.assertFalse(task.done())
                    from src.modules.supplier_sourcing.domain.supplier_source.value_object.name import (
                        SupplierSourceNameVO,
                    )

                    await SqlAlchemySupplierSourceRepository(session).save(
                        refreshed.rename(
                            SupplierSourceNameVO("Committed while waiting")
                        )
                    )
                    await session.commit()
                    response = await asyncio.wait_for(task, 5)
                    self.assertEqual(response.status_code, 200, response.text)
                    self.assertEqual(
                        (
                            response.json()["name"],
                            response.json()["default_lead_time_seconds"],
                        ),
                        ("Committed while waiting", 42),
                    )
                finally:
                    if not task.done():
                        task.cancel()
                        await asyncio.gather(task, return_exceptions=True)
        self.assertEqual(
            (await self.client.get(url)).json()["name"], "Committed while waiting"
        )

    async def create_contact(self, *, same_id: bool = False) -> dict:
        """Создаёт физлицо; совпадение UUID с компанией специально проверяет составной ключ."""
        if same_id:
            self.app.state.uuid_generator = Mock(
                new=Mock(return_value=UUID(self.company["id"]))
            )
        try:
            response = await self.client.post(
                "/api/console/crm/contacts",
                headers=self.headers,
                json={
                    "first_name": "Иван",
                    "last_name": "Петров",
                    "middle_name": "Иванович",
                },
            )
        finally:
            if same_id:
                del self.app.state.uuid_generator
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()

    async def test_same_uuid_different_types_create_read_and_filter_without_collision(
        self,
    ) -> None:
        """Публичные имена, фильтры и карточки различают одинаковые UUID двух таблиц."""
        contact = await self.create_contact(same_id=True)
        company_source = await self.create_source(name="Company source")
        contact_source = await self.create_source(
            name="Contact source",
            supplier_model_key="crm.contact",
            supplier_id=contact["id"],
        )
        page = (await self.client.get(self.base)).json()
        self.assertEqual(page["total"], 2)
        self.assertEqual(
            {
                (row["supplier_model_key"], row["supplier_name"])
                for row in page["items"]
            },
            {("crm.company", "Supplier ACME"), ("crm.contact", "Петров Иван Иванович")},
        )
        for source in (company_source, contact_source):
            self.assertEqual(
                (await self.client.get(f"{self.base}/{source['id']}")).json(), source
            )
            page = (
                await self.client.get(
                    self.base,
                    params={
                        "supplier_model_key": source["supplier_model_key"],
                        "supplier_id": source["supplier_id"],
                    },
                )
            ).json()
            self.assertEqual((page["total"], page["items"][0]["id"]), (1, source["id"]))
        response = await self.client.get(
            self.base, params={"supplier_id": contact["id"]}
        )
        self.assertEqual(response.status_code, 422, response.text)
        page = (
            await self.client.get(
                self.base, params={"supplier_model_key": "crm.contact"}
            )
        ).json()
        self.assertEqual(page["total"], 1)
        response = await self.client.get(
            "/api/console/crm/counterparty-references",
            params={"model_key": "crm.contact", "search": "петров Иван", "limit": 1},
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(
            response.json()["items"],
            [
                {
                    "model_key": "crm.contact",
                    "id": contact["id"],
                    "display_name": "Петров Иван Иванович",
                }
            ],
        )
        response = await self.client.patch(
            f"/api/console/crm/contacts/{contact['id']}",
            headers=self.headers,
            json={"last_name": "Сидоров"},
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(
            (await self.client.get(f"{self.base}/{contact_source['id']}")).json()[
                "supplier_name"
            ],
            "Сидоров Иван Иванович",
        )

    async def test_contact_source_does_not_block_same_uuid_company_but_blocks_contact(
        self,
    ) -> None:
        """Использование контакта не означает использование одноимённой по UUID компании."""
        contact = await self.create_contact(same_id=True)
        source = await self.create_source(
            supplier_model_key="crm.contact", supplier_id=contact["id"]
        )
        response = await self.client.delete(
            f"/api/console/crm/companies/{self.company['id']}", headers=self.headers
        )
        self.assertEqual(response.status_code, 204, response.text)
        response = await self.client.patch(
            f"{self.base}/{source['id']}",
            headers=self.headers,
            json={"is_active": False},
        )
        self.assertEqual(response.status_code, 200, response.text)
        with patch(
            "src.modules.crm.infrastructure.contact_point.adapter.ContactPointsAdapter.remove",
            side_effect=AssertionError("No side effects before usage guard"),
        ):
            response = await self.client.delete(
                f"/api/console/crm/contacts/{contact['id']}", headers=self.headers
            )
        self.assertEqual(response.status_code, 409, response.text)
        self.assertEqual(
            (await self.client.get(f"{self.base}/{source['id']}")).json()[
                "supplier_name"
            ],
            "Петров Иван Иванович",
        )

    async def test_company_source_does_not_block_same_uuid_contact(self) -> None:
        """Одинаковый UUID не создаёт ложного запрета удаления другого типа."""
        contact = await self.create_contact(same_id=True)
        await self.create_source()
        self.assertEqual(
            (
                await self.client.delete(
                    f"/api/console/crm/contacts/{contact['id']}", headers=self.headers
                )
            ).status_code,
            204,
        )
        self.assertEqual(
            (
                await self.client.delete(
                    f"/api/console/crm/companies/{self.company['id']}",
                    headers=self.headers,
                )
            ).status_code,
            409,
        )

    async def test_wrong_type_unknown_type_incomplete_key_and_immutable_owner(
        self,
    ) -> None:
        """Компания не подставляется вместо отсутствующего контакта; владелец неизменяем."""
        response = await self.client.post(
            self.base,
            headers=self.headers,
            json={**self.payload, "supplier_model_key": "crm.contact"},
        )
        self.assertEqual(response.status_code, 404, response.text)
        for body in (
            {
                key: value
                for key, value in self.payload.items()
                if key != "supplier_model_key"
            },
            {**self.payload, "supplier_model_key": "crm.deal"},
            {**self.payload, "supplier_model_key": None},
        ):
            response = await self.client.post(
                self.base, headers=self.headers, json=body
            )
            self.assertEqual(response.status_code, 422, response.text)
        source = await self.create_source()
        for field, value in [
            ("supplier_model_key", "crm.contact"),
            ("supplier_id", str(uuid4())),
        ]:
            response = await self.client.patch(
                f"{self.base}/{source['id']}", headers=self.headers, json={field: value}
            )
            self.assertEqual(response.status_code, 422, response.text)
        async with self.engine.begin() as connection:
            schema = self.schemas[0]
            count = await connection.scalar(
                text(
                    "SELECT count(*) FROM pg_constraint WHERE conrelid = to_regclass(:name) AND contype = 'f'"
                ),
                {"name": f"{schema}.supplier_sources"},
            )
            self.assertEqual(count, 0)
        for endpoint in (self.base, "/api/console/crm/counterparty-references"):
            params = (
                {"supplier_model_key": "crm.deal"}
                if endpoint == self.base
                else {"model_key": "crm.deal"}
            )
            self.assertEqual(
                (await self.client.get(endpoint, params=params)).status_code, 422
            )

    async def test_contact_validation_tenant_isolation_and_safe_search(self) -> None:
        """Ссылка на контакт и серверный поиск ограничены одним tenant."""
        contact = await self.create_contact()
        source = await self.create_source(
            supplier_model_key="crm.contact", supplier_id=contact["id"]
        )
        self.app.state.test_context = replace(
            self.context,
            principal=replace(self.context.principal, tenant_id=str(self.other)),
        )
        self.assertEqual(
            (
                await self.client.post(
                    self.base,
                    headers=self.headers,
                    json={
                        **self.payload,
                        "supplier_model_key": "crm.contact",
                        "supplier_id": contact["id"],
                    },
                )
            ).status_code,
            404,
        )
        response = await self.client.get(
            "/api/console/crm/counterparty-references",
            params={"model_key": "crm.contact"},
        )
        self.assertEqual(response.json()["total"], 0)
        self.assertEqual(
            (await self.client.get(f"{self.base}/{source['id']}")).status_code, 404
        )

    async def test_contact_lock_serializes_creation_and_delete_without_fk(self) -> None:
        """Создание удерживает запись контакта; удаление после ожидания видит новую ссылку."""
        contact = await self.create_contact()
        source = await self.create_source(
            supplier_model_key="crm.contact", supplier_id=contact["id"]
        )
        async with self.engine.begin() as connection:
            await bind_tenant_schema(connection, self.tenant.uuid, self.naming)
            async with async_sessionmaker(
                connection, expire_on_commit=False
            )() as session:
                aggregate = await SqlAlchemySupplierSourceRepository(
                    session
                ).get_for_update(SupplierSourceIdVO(UUID(source["id"])))
            await connection.execute(
                delete(SupplierSourceModel).where(
                    SupplierSourceModel.id == UUID(source["id"])
                )
            )
        async with self.engine.connect() as connection:
            await bind_tenant_schema(connection, self.tenant.uuid, self.naming)
            async with async_sessionmaker(
                connection, expire_on_commit=False
            )() as session:
                self.assertIsNotNone(
                    await SqlAlchemyCounterpartyReferenceRepository(session).get(
                        CounterpartyModelKey.CONTACT, UUID(contact["id"]), lock=True
                    )
                )
                task = asyncio.create_task(
                    self.client.delete(
                        f"/api/console/crm/contacts/{contact['id']}",
                        headers=self.headers,
                    )
                )
                try:
                    await asyncio.sleep(0.1)
                    self.assertFalse(task.done())
                    await SqlAlchemySupplierSourceRepository(session).add(aggregate)
                    await session.commit()
                    response = await asyncio.wait_for(task, 5)
                    self.assertEqual(response.status_code, 409, response.text)
                finally:
                    if not task.done():
                        task.cancel()
                        await asyncio.gather(task, return_exceptions=True)

    async def test_contact_deletion_wins_creation_does_not_leave_orphan(self) -> None:
        """Проверка после ожидания удалённой строки возвращает 404 без записи источника."""
        contact = await self.create_contact()
        async with self.engine.connect() as connection:
            await bind_tenant_schema(connection, self.tenant.uuid, self.naming)
            async with async_sessionmaker(
                connection, expire_on_commit=False
            )() as session:
                statement = (
                    select(ContactModel)
                    .where(ContactModel.id == UUID(contact["id"]))
                    .with_for_update()
                )
                self.assertIsNotNone((await session.scalars(statement)).one_or_none())
                task = asyncio.create_task(
                    self.client.post(
                        self.base,
                        headers=self.headers,
                        json={
                            **self.payload,
                            "supplier_model_key": "crm.contact",
                            "supplier_id": contact["id"],
                        },
                    )
                )
                try:
                    await asyncio.sleep(0.1)
                    self.assertFalse(task.done())
                    await session.execute(
                        delete(ContactModel).where(
                            ContactModel.id == UUID(contact["id"])
                        )
                    )
                    await session.commit()
                    response = await asyncio.wait_for(task, 5)
                    self.assertEqual(response.status_code, 404, response.text)
                finally:
                    if not task.done():
                        task.cancel()
                        await asyncio.gather(task, return_exceptions=True)
        self.assertEqual((await self.client.get(self.base)).json()["total"], 0)
