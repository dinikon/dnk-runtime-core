"""Диагностика XML-ключей через настоящий SQL, HTTP и фоновые чтения."""

import os
import unittest
from uuid import UUID, uuid4
from sqlalchemy import insert, select, update
from test import test_channels_postgres as core
from test import test_channels_content_update_postgres as content
from src.modules.channels.infrastructure.persistence.models.external_publication import (
    ExternalPublicationModel as P,
)
from src.modules.channels.infrastructure.persistence.models.sync_run import SyncRunModel
from src.modules.channels.infrastructure.persistence.models.connection import (
    ConnectionModel,
)


@unittest.skipUnless(
    os.environ.get("TEST_POSTGRES_URL"), "Requires disposable PostgreSQL"
)
class PublicationIdentityPostgresTests(unittest.IsolatedAsyncioTestCase):
    """Проверяет область коллизий, полноту чтения и отсутствие побочных записей."""

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

    async def page(self, connection_id: str, **filters: str | int) -> dict:
        """Читает публичную проекцию с реальными query-параметрами."""
        response = await self.client.get(
            f"/api/console/channels/connections/{connection_id}/publications",
            params=filters,
            headers=self.headers,
        )
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    async def test_global_duplicates_filters_and_read_only_projection(self) -> None:
        """Связь, поиск и страницы не скрывают коллизии; ключи сохраняют точные строки."""
        _, pubs, _ = await self.setup_bound("prom")
        connection_id = pubs[0]["connection_id"]
        async with self.session() as session:
            rows = (await session.execute(select(P.__table__))).mappings().all()
            source = dict(rows[0])
            for row in rows:
                meta = dict(row["meta"])
                meta["provider"] = {**meta["provider"], "import_key": "00042"}
                await session.execute(
                    update(P).where(P.id == row["id"]).values(meta=meta)
                )
            # Пустые значения не образуют ложную duplicate-группу, "0" — настоящий ключ.
            for number, key in enumerate(
                (None, "", " \t\n\u00a0", "0", "42", "Case", "case")
            ):
                row = {**source, "id": uuid4(), "external_id": f"extra-{number}"}
                row["meta"] = {**source["meta"], "provider": {"import_key": key}}
                await session.execute(insert(P).values(**row))
            before = (
                (await session.execute(select(P.__table__).order_by(P.id)))
                .mappings()
                .all()
            )
        other_channel, other_connection = await self.create("prom")
        await self.drain()
        # Такой же ключ в другом Connection не увеличивает число конфликтов.
        async with self.session() as session:
            await session.execute(
                update(P)
                .where(P.connection_id == UUID(other_connection["connection_id"]))
                .values(meta={"provider": {"import_key": "00042"}, "read_issues": []})
            )
        full = await self.page(connection_id, limit=1)
        summary = full["identity_summary"]
        self.assertEqual(
            (
                summary["total"],
                summary["missing"],
                summary["duplicate"],
                summary["valid"],
                summary["duplicate_groups"],
            ),
            (10, 3, 3, 4, 1),
        )
        for filters in (
            {"binding_status": "bound"},
            {"binding_status": "unbound"},
            {"search": pubs[0]["external_id"]},
            {"offset": 2},
        ):
            page = await self.page(
                connection_id, limit=1, identity_status="duplicate", **filters
            )
            self.assertEqual(page["identity_summary"], summary)
            for item in page["items"]:
                self.assertEqual(
                    item["identity"],
                    {"state": "duplicate", "key": "00042", "conflict_count": 2},
                )
                self.assertNotIn("meta", item)
        duplicate = await self.page(
            connection_id, identity_status="duplicate", identity_key="00042"
        )
        self.assertEqual(duplicate["total"], 3)
        for key in ("0", "42", "Case", "case"):
            page = await self.page(
                connection_id, identity_status="valid", identity_key=key
            )
            self.assertEqual(page["total"], 1)
            self.assertEqual(page["items"][0]["identity"]["key"], key)
        detail = await self.request("GET", f"/publications/{pubs[0]['publication_id']}")
        self.assertEqual(detail["identity"]["conflict_count"], 2)
        async with self.session() as session:
            after = (
                (
                    await session.execute(
                        select(P.__table__)
                        .where(P.connection_id == UUID(connection_id))
                        .order_by(P.id)
                    )
                )
                .mappings()
                .all()
            )
        self.assertEqual(after, before)
        self.assertFalse(
            (await self.request("GET", "/" + other_channel["channel_id"]))["is_enabled"]
        )

    async def test_reimport_recomputes_diagnostics_preserving_binding(self) -> None:
        """Повторное чтение исправленного provider external_id снимает предупреждение."""
        _, pubs, _ = await self.setup_bound("prom")
        publication = pubs[0]
        connection_id = publication["connection_id"]
        async with self.session() as session:
            row = (
                (
                    await session.execute(
                        select(P.__table__).where(
                            P.id == UUID(publication["publication_id"])
                        )
                    )
                )
                .mappings()
                .one()
            )
            await session.execute(
                update(P)
                .where(P.id == row["id"])
                .values(
                    meta={
                        **row["meta"],
                        "provider": {**row["meta"]["provider"], "import_key": None},
                    }
                )
            )
        missing = await self.page(connection_id, identity_status="missing")
        self.assertEqual(missing["total"], 1)
        binding_fields = ("binding_id", "representation_id", "catalog_item_id")
        binding = {field: missing["items"][0][field] for field in binding_fields}
        await self.request(
            "POST",
            f"/connections/{connection_id}/initialization",
            {"request_key": str(uuid4())},
            202,
        )
        await self.drain()
        self.assertEqual(
            (await self.page(connection_id, identity_status="missing"))["total"], 0
        )
        refreshed = await self.page(connection_id, search=publication["external_id"])
        self.assertEqual(
            refreshed["items"][0]["publication_id"], publication["publication_id"]
        )
        self.assertEqual(
            {field: refreshed["items"][0][field] for field in binding_fields}, binding
        )
        self.assertEqual(refreshed["items"][0]["identity"]["state"], "valid")

    async def test_completeness_woo_and_invalid_filters(self) -> None:
        """Неполный снимок не объявляет глобальную уникальность; Woo не требует ключа."""
        _, connection = await self.create("prom")
        connection_id = connection["connection_id"]
        self.assertEqual(
            (await self.page(connection_id))["identity_summary"]["assessment"],
            "not_started",
        )
        await self.drain()
        self.assertEqual(
            (await self.page(connection_id))["identity_summary"]["assessment"],
            "current",
        )
        for values, expected in (
            ({"status": "running", "read_complete": False}, "in_progress"),
            ({"status": "partial", "read_complete": False}, "incomplete"),
            ({"status": "partial", "read_complete": True, "invalid": 1}, "incomplete"),
            ({"invalid": 0, "read_complete": True}, "current"),
        ):
            async with self.session() as session:
                await session.execute(
                    update(SyncRunModel)
                    .where(SyncRunModel.connection_id == UUID(connection_id))
                    .values(**values)
                )
            self.assertEqual(
                (await self.page(connection_id))["identity_summary"]["assessment"],
                expected,
            )
        async with self.session() as session:
            await session.execute(
                update(ConnectionModel)
                .where(ConnectionModel.id == UUID(connection_id))
                .values(generation=2)
            )
        self.assertEqual(
            (await self.page(connection_id))["identity_summary"]["assessment"], "stale"
        )
        _, woo = await self.create("woocommerce")
        await self.drain()
        page = await self.page(woo["connection_id"], identity_status="not_required")
        self.assertIsNone(page["identity_summary"])
        self.assertGreater(page["total"], 0)
        self.assertTrue(
            all(item["identity"]["state"] == "not_required" for item in page["items"])
        )
        for filters in (
            {"identity_status": "ready"},
            {"identity_key": ""},
            {"identity_key": "x" * 513},
        ):
            response = await self.client.get(
                f"/api/console/channels/connections/{connection_id}/publications",
                params=filters,
                headers=self.headers,
            )
            self.assertEqual(response.status_code, 422, response.text)
