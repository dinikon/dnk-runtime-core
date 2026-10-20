"""Backfill и JSONB-проекции на настоящей одноразовой PostgreSQL-базе."""

import os
import unittest
from uuid import UUID, uuid4
from sqlalchemy import select, text, update
from test import test_channels_postgres as core
from test import test_channels_content_update_postgres as content
from src.modules.channels.infrastructure.persistence.models.external_publication import (
    ExternalPublicationModel as P,
)
from src.modules.channels.infrastructure.external_publication.persistence.mapper import (
    ExternalPublicationMapper,
)
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_migrations import (
    TenantMigrator,
)


@unittest.skipUnless(
    os.environ.get("TEST_POSTGRES_URL"), "Requires disposable PostgreSQL"
)
class PublicationPayloadPostgresTests(unittest.IsolatedAsyncioTestCase):
    """Проверяет обновление схемы с существующими связями и историей операций."""

    asyncSetUp = content.ChannelsContentUpdatePostgresTests.asyncSetUp
    asyncTearDown = core.ChannelsPostgresTests.asyncTearDown
    session = core.ChannelsPostgresTests.session
    request = core.ChannelsPostgresTests.request
    create = core.ChannelsPostgresTests.create
    claim = core.ChannelsPostgresTests.claim
    drain = core.ChannelsPostgresTests.drain
    deliver = content.ChannelsContentUpdatePostgresTests.deliver
    catalog = content.ChannelsContentUpdatePostgresTests.catalog
    setup_bound = content.ChannelsContentUpdatePostgresTests.setup_bound
    prepare = content.ChannelsContentUpdatePostgresTests.prepare

    async def test_legacy_backfill_preserves_identity_bindings_and_history(
        self,
    ) -> None:
        """0031 → 0032 сохраняет данные и связи обоих плагинов, без ложной ревизии."""
        channels = []
        for kind in ("prom", "woocommerce"):
            channel, publications, _ = await self.setup_bound(kind)
            await self.prepare(channel, publications)
            channels.append((kind, channel, publications))
        schema = self.schemas[self.tenant]
        history_tables = (
            "channel_product_representations",
            "channel_external_bindings",
            "channel_content_update_runs",
            "channel_content_update_items",
        )
        async with self.engine.begin() as connection:
            before = {
                table: (
                    await connection.execute(
                        text(f'SELECT * FROM "{schema}".{table} ORDER BY 1')
                    )
                )
                .mappings()
                .all()
                for table in history_tables
            }
            migrator = TenantMigrator()
            await migrator.downgrade(connection, schema, "0031_channel_content_updates")
            # Удаляем только мост отката: симулируем настоящий релиз 0031, а не roundtrip нового снимка.
            await connection.execute(
                text(
                    f'UPDATE "{schema}".channel_external_publications '
                    "SET extensions=extensions - '_channels_payload_v1'"
                )
            )
            legacy = {
                row["id"]: row
                for row in (
                    await connection.execute(
                        text(
                            f'SELECT * FROM "{schema}".channel_external_publications ORDER BY id'
                        )
                    )
                ).mappings()
            }
            await migrator.upgrade(connection, schema)
            for table in history_tables:
                self.assertEqual(
                    (
                        await connection.execute(
                            text(f'SELECT * FROM "{schema}".{table} ORDER BY 1')
                        )
                    )
                    .mappings()
                    .all(),
                    before[table],
                )
            rows = (
                (
                    await connection.execute(
                        text(f'SELECT * FROM "{schema}".channel_external_publications')
                    )
                )
                .mappings()
                .all()
            )
            self.assertEqual({row["id"] for row in rows}, set(legacy))
            for row in rows:
                previous = legacy[row["id"]]
                publication = ExternalPublicationMapper.to_domain(row)
                for key in (
                    "connection_id",
                    "resource_type",
                    "external_id",
                    "observed_revision",
                    "first_seen_at",
                    "last_seen_at",
                    "last_import_run_id",
                    "source_updated_at",
                ):
                    self.assertEqual(row[key], previous[key])
                for key in (
                    "external_sku",
                    "price",
                    "sale_price",
                    "currency",
                    "quantity",
                    "stock_status",
                    "title",
                    "title_locale",
                    "main_image_url",
                ):
                    self.assertEqual(getattr(publication.core, key), previous[key])
                    self.assertNotIn(key, row)
                self.assertEqual(
                    publication.meta.read_issues, tuple(previous["warnings"])
                )
                provider = dict(previous["extensions"])
                if previous["extension_version"] == "prom.read.v1":
                    provider["import_key"] = provider.pop("provider_external_id")
                self.assertEqual(publication.meta.provider, provider)
            snapshots = {
                row["id"]: (row["payload"], row["meta"], row["fingerprint"])
                for row in rows
            }
            await migrator.downgrade(connection, schema, "0031_channel_content_updates")
            await migrator.upgrade(connection, schema)
            roundtrip = (
                (
                    await connection.execute(
                        text(f'SELECT * FROM "{schema}".channel_external_publications')
                    )
                )
                .mappings()
                .all()
            )
            self.assertEqual(
                {
                    row["id"]: (row["payload"], row["meta"], row["fingerprint"])
                    for row in roundtrip
                },
                snapshots,
            )
        for kind, _, publications in channels:
            if kind != "woocommerce":
                continue
            connection_id = publications[0]["connection_id"]
            await self.request(
                "POST",
                f"/connections/{connection_id}/initialization",
                {"request_key": str(uuid4())},
                202,
            )
            await self.drain()
        async with self.session() as session:
            after = (await session.execute(select(P.__table__))).mappings().all()
            self.assertEqual(
                {row["id"]: row["observed_revision"] for row in after},
                {
                    identifier: row["observed_revision"]
                    for identifier, row in legacy.items()
                },
            )

    async def test_json_search_and_secondary_locale_survive_schema_roundtrip(
        self,
    ) -> None:
        """JSONB-фильтры выполняются до пагинации; неизвестный язык не подставляется."""
        _, pubs, _ = await self.setup_bound("prom")
        pub = pubs[0]
        async with self.session() as session:
            payload = await session.scalar(
                select(P.payload).where(P.id == UUID(pub["publication_id"]))
            )
            payload["sku"] = "literal_%_sku"
            payload["titles"] = {"ru": "Название_%", "uk": "Назва"}
            payload["stock"] = {"quantity": "0", "status": "out_of_stock"}
            await session.execute(
                update(P)
                .where(P.id == UUID(pub["publication_id"]))
                .values(payload=payload)
            )
        schema = self.schemas[self.tenant]
        async with self.engine.begin() as connection:
            migrator = TenantMigrator()
            await migrator.downgrade(connection, schema, "0031_channel_content_updates")
            await migrator.upgrade(connection, schema)
        for search in ("literal_%_sku", "Название_%"):
            response = await self.client.get(
                f"/api/console/channels/connections/{pub['connection_id']}/publications",
                params={"search": search, "stock_status": "out_of_stock", "limit": 1},
                headers=self.headers,
            )
            self.assertEqual(response.status_code, 200, response.text)
            page = response.json()
            self.assertEqual(page["total"], 1)
            self.assertEqual(page["items"][0]["publication_id"], pub["publication_id"])
            self.assertEqual(page["items"][0]["title"], "Название_%")
            self.assertNotIn("meta", page["items"][0])
            self.assertNotIn("payload", page["items"][0])
        async with self.session() as session:
            payload = await session.scalar(
                select(P.payload).where(P.id == UUID(pub["publication_id"]))
            )
            self.assertEqual(payload["titles"], {"ru": "Название_%", "uk": "Назва"})
        detail = await self.request("GET", f"/publications/{pub['publication_id']}")
        self.assertEqual(detail["title"], "Название_%")
        self.assertNotIn("extensions", detail)
        self.assertNotIn("meta", detail)
