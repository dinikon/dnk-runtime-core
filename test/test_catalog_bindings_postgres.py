"""Реальный HTTP и PostgreSQL: сопоставления, блокировки и владение данными."""

from dataclasses import replace
import asyncio
import unittest
from datetime import datetime, UTC
from uuid import UUID, uuid4
from sqlalchemy import select, insert, update
from test.test_channels_postgres import ChannelsPostgresTests
from test.catalog_support import initialize_catalog
from src.modules.catalog.presentation.router import router as catalog_router
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_connection import (
    bind_tenant_schema,
)
from src.modules.channels.infrastructure.persistence.models.connection import (
    ConnectionModel,
)
from src.modules.channels.infrastructure.persistence.models.sync_run import SyncRunModel
from src.modules.channels.infrastructure.persistence.models.external_publication import (
    ExternalPublicationModel as P,
)
from src.modules.channels.domain.external_publication.value_object import (
    PublicationData,
    PublicationTitle,
)


class CatalogBindingsPostgresTests(ChannelsPostgresTests):
    async def asyncSetUp(self):
        await super().asyncSetUp()
        self.app.include_router(catalog_router, prefix="/api/console")
        for tenant in (self.tenant, self.other):
            async with self.sessions() as session:
                await bind_tenant_schema(
                    await session.connection(), tenant, self.naming
                )
                await initialize_catalog(
                    session, EntityIdVO(tenant), EntityIdVO(self.actor)
                )
                await session.commit()

    async def call(self, method, path, body=None, status=200):
        response = await self.client.request(
            method, "/api/console" + path, headers=self.headers, json=body
        )
        self.assertEqual(response.status_code, status, response.text)
        return response.json() if status != 204 else None

    async def catalog(self, variable=False, archived=False):
        body = {
            "kind": "variable" if variable else "simple",
            "status": "archived" if archived else "draft",
        }
        if variable:
            body["variants"] = [
                {"sku": "S-" + str(uuid4())},
                {"sku": "M-" + str(uuid4())},
            ]
        root = (await self.call("POST", "/catalog/items", body, 201))["id"]
        ids = (
            [
                v["id"]
                for v in (
                    await self.call("GET", f"/catalog/items/{root}/variants?locale=uk")
                )["items"]
            ]
            if variable
            else [root]
        )
        return root, ids

    async def source(self, platform="prom", variable=False, existing_channel=None):
        endpoint = {
            "prom": "https://my.prom.ua",
            "woocommerce": "https://shop.example",
            "rozetka": "https://api-seller.rozetka.com.ua",
        }[platform]
        credentials = (
            {"consumer_key": "test", "consumer_secret": "test"}
            if platform == "woocommerce"
            else {"token": "test"}
        )
        if existing_channel is None:
            channel = await self.call(
                "POST",
                "/channels",
                {
                    "name": platform,
                    "platform_kind": platform,
                    "config": {"version": 1, "endpoint": endpoint, "settings": {}},
                    "credentials": credentials,
                },
                201,
            )
            channel_id = channel["id"]
        else:
            channel_id = existing_channel
        ids = [uuid4(), uuid4()] if variable else [uuid4()]
        async with self.sessions() as session:
            await bind_tenant_schema(
                await session.connection(), self.tenant, self.naming
            )
            connection = await session.scalar(
                select(ConnectionModel.id).where(
                    ConnectionModel.channel_id == UUID(channel_id)
                )
            )
            now = datetime.now(UTC)
            run = uuid4()
            await session.execute(
                insert(SyncRunModel).values(
                    id=run,
                    connection_id=connection,
                    config_revision=1,
                    revision=1,
                    status="completed",
                    current_job_id=uuid4(),
                    checkpoint_version=1,
                    checkpoint={},
                    processed_count=len(ids),
                    skipped_count=0,
                    pages_count=1,
                    automatic=False,
                    error_code=None,
                    created_at=now,
                    started_at=now,
                    finished_at=now,
                )
            )
            for i, identifier in enumerate(ids):
                kind = (
                    "variable"
                    if variable and i == 0 and platform == "woocommerce"
                    else "variant" if variable and i else "simple"
                )
                data = PublicationData(
                    (PublicationTitle("uk", f"P{i}"),), "UAH", sku=f"P{i}"
                ).to_document()
                await session.execute(
                    insert(P).values(
                        id=identifier,
                        connection_id=connection,
                        resource_type="product",
                        external_id=str(identifier),
                        kind=kind,
                        parent_id=ids[0] if variable and i else None,
                        revision=1,
                        raw_data={},
                        normalized_schema="publication.v1",
                        normalized_data=data,
                        platform_schema="test.v1",
                        platform_data={},
                        first_seen_at=now,
                        last_seen_at=now,
                        last_sync_run_id=run,
                    )
                )
            await session.commit()
        return channel_id, [str(v) for v in ids]

    async def propose(
        self,
        channel,
        root,
        positions,
        pubs,
        mode="SIMPLE_TO_SIMPLE",
        source_root=None,
        group_id=None,
    ):
        items = [
            {"catalog_position_id": a, "publication_id": b}
            for a, b in zip(positions, pubs)
        ]
        payload = {
            "catalog_root_id": root,
            "mode": mode,
            "publication_root_id": source_root
            or (pubs[0] if mode != "VARIABLE_TO_SIMPLE" else None),
            "items": items,
            "locale": "uk",
            "group_id": group_id,
        }
        result = await self.call(
            "POST", f"/channels/{channel}/catalog-bindings/preview", payload
        )
        return payload, result["preview"]

    async def test_simple_repeat_groups_guards_and_lost_response(self):
        root, positions = await self.catalog(archived=True)
        channel, pubs = await self.source()
        payload, preview = await self.propose(channel, root, positions, pubs)
        self.assertEqual(preview["assessment"]["state"], "linked")
        create = {k: v for k, v in payload.items() if k != "group_id"} | {
            "catalog_token": preview["catalog_token"],
            "publication_token": preview["publication_token"],
        }
        group = await self.call(
            "POST", f"/channels/{channel}/catalog-bindings", create, 201
        )
        await self.call("POST", f"/channels/{channel}/catalog-bindings", create, 409)
        await self.call("DELETE", f"/catalog/items/{root}", status=409)
        page = await self.call(
            "GET", f"/channels/catalog-bindings?catalog_item_id={root}&locale=uk"
        )
        self.assertEqual(page["total"], 1)
        self.assertEqual(
            page["items"][0]["preview"]["catalog"]["root"]["status"], "archived"
        )
        await self.call(
            "PUT",
            f"/channels/{channel}/catalog-bindings/{group['id']}",
            {
                "items": payload["items"],
                "expected_revision": 1,
                "catalog_token": preview["catalog_token"],
                "publication_token": preview["publication_token"],
                "locale": "uk",
            },
        )
        await self.call(
            "DELETE",
            f"/channels/{channel}/catalog-bindings/{group['id']}?expected_revision=2",
            status=409,
        )
        await self.call(
            "DELETE",
            f"/channels/{channel}/catalog-bindings/{group['id']}?expected_revision=1",
            status=204,
        )
        await self.call(
            "DELETE",
            f"/channels/{channel}/catalog-bindings/{group['id']}?expected_revision=1",
            status=204,
        )
        await self.call("DELETE", f"/catalog/items/{root}", status=204)

    async def test_modes_three_platforms_and_structural_tokens(self):
        for platform in ("prom", "woocommerce", "rozetka"):
            root, variants = await self.catalog(variable=True)
            channel, pubs = await self.source(platform, variable=platform != "rozetka")
            mode = (
                "VARIABLE_TO_SIMPLE"
                if platform == "rozetka"
                else "VARIABLE_TO_VARIABLE"
            )
            sellable = (
                pubs
                if platform == "prom"
                else pubs[1:] if platform == "woocommerce" else pubs
            )
            payload, preview = await self.propose(
                channel,
                root,
                variants,
                sellable,
                mode,
                source_root=pubs[0] if mode != "VARIABLE_TO_SIMPLE" else None,
            )
            self.assertEqual(
                preview["assessment"]["state"],
                "linked" if platform == "prom" else "partial",
            )
            create = {k: v for k, v in payload.items() if k != "group_id"} | {
                "catalog_token": preview["catalog_token"],
                "publication_token": preview["publication_token"],
            }
            group = await self.call(
                "POST", f"/channels/{channel}/catalog-bindings", create, 201
            )
            await self.call(
                "DELETE", f"/catalog/items/{root}/variants/{variants[0]}", status=409
            )
            await self.call(
                "PATCH",
                f"/catalog/items/{root}/variants/{variants[0]}",
                {"status": "archived"},
            )
            read = await self.call(
                "GET", f"/channels/{channel}/catalog-bindings/{group['id']}?locale=uk"
            )
            self.assertEqual(
                read["binding"]["preview"]["assessment"]["state"],
                preview["assessment"]["state"],
            )
            added = await self.call("POST", f"/catalog/items/{root}/variants", {}, 201)
            update_payload = {
                "expected_revision": 1,
                "items": payload["items"],
                "catalog_token": preview["catalog_token"],
                "publication_token": preview["publication_token"],
                "locale": "uk",
            }
            await self.call(
                "PUT",
                f"/channels/{channel}/catalog-bindings/{group['id']}",
                update_payload,
                409,
            )
            await self.call(
                "DELETE", f'/catalog/items/{root}/variants/{added["id"]}', status=204
            )
            # Native roles change without deleting the stored association.
            async with self.sessions() as session:
                await bind_tenant_schema(
                    await session.connection(), self.tenant, self.naming
                )
                await session.execute(
                    update(P).where(P.id == UUID(sellable[0])).values(kind="variable")
                )
                await session.commit()
            read = await self.call(
                "GET", f"/channels/{channel}/catalog-bindings/{group['id']}?locale=uk"
            )
            self.assertEqual(
                read["binding"]["preview"]["assessment"]["state"], "conflict"
            )
            await self.call(
                "DELETE",
                f"/channels/{channel}/catalog-bindings/{group['id']}?expected_revision=1",
                status=204,
            )

    async def test_candidates_and_concurrent_claim(self):
        root, positions = await self.catalog()
        channel, pubs = await self.source("woocommerce")
        candidates = await self.call(
            "GET",
            f"/channels/{channel}/publication-binding-candidates?mode=SIMPLE_TO_SIMPLE&locale=uk",
        )
        self.assertEqual(candidates["total"], 1)
        catalog = await self.call(
            "GET",
            f"/channels/{channel}/catalog-binding-candidates?mode=SIMPLE_TO_SIMPLE&locale=uk",
        )
        self.assertTrue(any(v["id"] == root for v in catalog["items"]))
        payload, preview = await self.propose(channel, root, positions, pubs)
        create = {k: v for k, v in payload.items() if k != "group_id"} | {
            "catalog_token": preview["catalog_token"],
            "publication_token": preview["publication_token"],
        }
        results = await asyncio.gather(
            *(
                self.client.post(
                    f"/api/console/channels/{channel}/catalog-bindings",
                    headers=self.headers,
                    json=create,
                )
                for _ in range(2)
            )
        )
        self.assertEqual(sorted(v.status_code for v in results), [201, 409])

    async def create_binding(
        self, channel, root, positions, pubs, mode="SIMPLE_TO_SIMPLE", source_root=None
    ):
        payload, preview = await self.propose(
            channel, root, positions, pubs, mode, source_root
        )
        return await self.call(
            "POST",
            f"/channels/{channel}/catalog-bindings",
            {k: v for k, v in payload.items() if k != "group_id"}
            | {
                "catalog_token": preview["catalog_token"],
                "publication_token": preview["publication_token"],
            },
            201,
        )

    async def test_reuse_catalog_in_independent_groups_and_filter_before_pagination(
        self,
    ):
        root, positions = await self.catalog()
        channel, pubs = await self.source()
        _, second = await self.source(existing_channel=channel)
        _, third = await self.source(existing_channel=channel)
        first = await self.create_binding(channel, root, positions, pubs)
        another = await self.create_binding(channel, root, positions, second)
        groups = await self.call(
            "GET", f"/channels/catalog-bindings?catalog_item_id={root}"
        )
        self.assertEqual(groups["total"], 2)
        linked = await self.call(
            "GET", f"/channels/{channel}/publications?binding=linked&limit=1"
        )
        self.assertEqual((linked["total"], len(linked["items"])), (2, 1))
        self.assertEqual(linked["items"][0]["bindings"][0]["state"], "linked")
        unlinked = await self.call(
            "GET", f"/channels/{channel}/publications?binding=unlinked&limit=1"
        )
        self.assertEqual(unlinked["total"], 1)
        self.assertEqual(unlinked["items"][0]["id"], third[0])
        self.assertEqual(unlinked["items"][0]["bindings"], [])
        detail = await self.call("GET", f"/channels/{channel}/publications/{pubs[0]}")
        self.assertEqual(detail["card"]["bindings"][0]["id"], first["id"])
        # A different Catalog family cannot take an already claimed source.
        other_root, other_positions = await self.catalog()
        payload, preview = await self.propose(
            channel, other_root, other_positions, pubs
        )
        self.assertIn("binding_publication_occupied", preview["assessment"]["issues"])
        # Tenant identifiers never cross the schema boundary.
        self.app.state.test_context = replace(
            self.context,
            principal=replace(self.context.principal, tenant_id=str(self.other)),
        )
        response = await self.client.get(
            f"/api/console/channels/{channel}/catalog-bindings/{another['id']}"
        )
        self.assertEqual(response.status_code, 404, response.text)
        self.app.state.test_context = self.context
        await self.call(
            "DELETE", f"/channels/{channel}?expected_revision=1", status=204
        )
        self.assertEqual(
            (
                await self.call(
                    "GET", f"/channels/catalog-bindings?catalog_item_id={root}"
                )
            )["total"],
            0,
        )
        await self.call("GET", f"/catalog/items/{root}?locale=uk")

    async def test_variable_to_simple_on_every_platform_reuses_variants_between_groups(
        self,
    ):
        for platform in ("prom", "woocommerce", "rozetka"):
            root, variants = await self.catalog(variable=True)
            channel, pubs = await self.source(platform)
            _, second = await self.source(platform, existing_channel=channel)
            first = await self.create_binding(
                channel, root, variants[:1], pubs, "VARIABLE_TO_SIMPLE"
            )
            await self.create_binding(
                channel, root, variants[:1], second, "VARIABLE_TO_SIMPLE"
            )
            groups = await self.call(
                "GET", f"/channels/catalog-bindings?catalog_item_id={root}"
            )
            self.assertEqual(groups["total"], 2)
            self.assertTrue(
                all(
                    g["preview"]["assessment"]["state"] == "partial"
                    for g in groups["items"]
                )
            )
            # Actual pair replacement raises revision once and releases previous source.
            _, third = await self.source(platform, existing_channel=channel)
            payload, preview = await self.propose(
                channel,
                root,
                variants[1:],
                third,
                "VARIABLE_TO_SIMPLE",
                group_id=first["id"],
            )
            result = await self.call(
                "PUT",
                f"/channels/{channel}/catalog-bindings/{first['id']}",
                {
                    "items": payload["items"],
                    "expected_revision": 1,
                    "catalog_token": preview["catalog_token"],
                    "publication_token": preview["publication_token"],
                    "locale": "uk",
                },
            )
            self.assertEqual(result["revision"], 2)
            candidate = await self.call(
                "GET",
                f"/channels/{channel}/publication-binding-candidates?mode=VARIABLE_TO_SIMPLE",
            )
            self.assertNotIn(pubs[0], candidate["occupied_ids"])
            await self.call(
                "DELETE",
                f"/channels/{channel}/catalog-bindings/{first['id']}?expected_revision=1",
                status=409,
            )

    async def test_http_boundaries_and_migration_round_trip(self):
        from src.modules.tenancy.infrastructure.tenant.persistence.tenant_migrations import (
            TenantMigrator,
        )

        root, positions = await self.catalog()
        channel, pubs = await self.source("prom")
        other_channel, foreign = await self.source("prom")
        payload, preview = await self.propose(channel, root, positions, pubs)
        body = {k: v for k, v in payload.items() if k != "group_id"} | {
            "catalog_token": preview["catalog_token"],
            "publication_token": preview["publication_token"],
        }
        no_csrf = await self.client.post(
            f"/api/console/channels/{channel}/catalog-bindings", json=body
        )
        self.assertEqual(no_csrf.status_code, 403)
        await self.call(
            "POST",
            f"/channels/{channel}/catalog-bindings",
            body | {"credentials": {"token": "must-not-leak"}},
            422,
        )
        _, invalid = await self.propose(channel, root, positions, foreign)
        self.assertIn(
            "binding_publication_root_invalid", invalid["assessment"]["issues"]
        )
        group = await self.call(
            "POST", f"/channels/{channel}/catalog-bindings", body, 201
        )
        page = await self.call(
            "GET", f"/channels/{channel}/catalog-bindings?mode=SIMPLE_TO_SIMPLE&limit=1"
        )
        self.assertEqual(page["total"], 1)
        none = await self.call(
            "GET",
            f"/channels/{channel}/catalog-bindings?mode=VARIABLE_TO_SIMPLE&limit=1",
        )
        self.assertEqual(none["total"], 0)
        response = await self.call(
            "POST",
            f"/channels/{channel}/catalog-bindings/preview",
            payload | {"group_id": group["id"], "catalog_root_id": str(uuid4())},
            422,
        )
        self.assertEqual(response["detail"]["code"], "binding_anchors_immutable")
        async with self.engine.begin() as connection:
            await TenantMigrator().downgrade(
                connection, self.schemas[0], "0008_catalog_variants"
            )
        self.assertEqual(len(await self.rows(P)), 2)
        await self.call("GET", f"/catalog/items/{root}?locale=uk")
        async with self.engine.begin() as connection:
            await TenantMigrator().upgrade(connection, self.schemas[0])
        self.assertEqual(
            (await self.call("GET", f"/channels/{channel}/catalog-bindings"))["total"],
            0,
        )
        self.assertEqual(len(await self.rows(P)), 2)


def load_tests(loader, tests, pattern):
    return unittest.TestSuite(
        CatalogBindingsPostgresTests(name)
        for name in CatalogBindingsPostgresTests.__dict__
        if name.startswith("test_")
    )
