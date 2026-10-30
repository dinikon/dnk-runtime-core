"""Полный HTTP → Catalog/Outbox → Inbox → Worker поток на отдельной PostgreSQL."""

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4
import asyncio
from dataclasses import replace
import json
from pathlib import Path
from unittest.mock import patch
from sqlalchemy import select, update

from test import test_catalog_bindings_postgres as support
from test.test_channels import FixtureHttp
from src.modules.channels.domain.channel.value_object.resource_identity import (
    ResourceIdentityVO,
)
from src.modules.channels.infrastructure.channel.persistence.repository import (
    SqlAlchemyChannelRepository,
)
from src.modules.channels.infrastructure.persistence.models.external_publication import (
    ExternalPublicationModel,
)
from src.modules.channels.infrastructure.persistence.models.connection import (
    ConnectionModel,
)
from src.modules.channels.infrastructure.persistence.models.stock_sync import (
    StockSyncModel,
)
from src.modules.channels.infrastructure.registry import InstalledPlatforms
from src.modules.channels.presentation.stock_sync.jobs import (
    ChannelsStockJobHandler,
    ChannelsCatalogStockChangedJobHandler,
)
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.shared.infrastructure.jobs.scheduled_job_model import ScheduledJobModel
from src.modules.shared.infrastructure.jobs.sqlalchemy_scheduled_job_repository import (
    SqlAlchemyScheduledJobRepository,
)
from src.modules.shared.infrastructure.events.integration_outbox_event_model import (
    IntegrationOutboxEventModel,
)
from src.modules.shared.infrastructure.events.integration_inbox_event_model import (
    IntegrationInboxEventModel,
)
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_connection import (
    bind_tenant_schema,
)


class ChannelStockPostgresTests(support.CatalogBindingsPostgresTests):
    async def asyncSetUp(self) -> None:
        await super().asyncSetUp()
        self.claimed_jobs = []
        async with self.engine.begin() as connection:
            for model in (IntegrationOutboxEventModel, IntegrationInboxEventModel):
                await connection.run_sync(
                    lambda c, model=model: model.__table__.create(c, checkfirst=True)
                )

    async def asyncTearDown(self) -> None:
        from sqlalchemy import delete

        async with self.engine.begin() as connection:
            for model in (IntegrationInboxEventModel, IntegrationOutboxEventModel):
                await connection.execute(
                    delete(model).where(model.tenant_id.in_((self.tenant, self.other)))
                )
        await super().asyncTearDown()

    async def setup_stock(
        self, platform: str = "woocommerce", tracked: bool = True
    ) -> tuple[str, str, str, str]:
        root = (
            await self.call(
                "POST",
                "/catalog/items",
                {
                    "stock": {
                        "manage_stock": tracked,
                        "stock_quantity": 7 if tracked else None,
                        "stock_status": None if tracked else "in_stock",
                        "backorders": "no",
                    }
                },
                201,
            )
        )["id"]
        channel, pubs = await self.source(platform=platform)
        async with self.sessions() as session:
            await bind_tenant_schema(
                await session.connection(), self.tenant, self.naming
            )
            repository = SqlAlchemyChannelRepository(session, self.tenant)
            aggregate = await repository.get(EntityIdVO(UUID(channel)), for_update=True)
            aggregate.apply_verification(
                job_id=aggregate.connection.verification.job_id,
                config_revision=1,
                identity=ResourceIdentityVO(namespace="test.stock", key=str(uuid4())),
                error_code=None,
                now=datetime.now(UTC),
            )
            await repository.save(aggregate)
            pub = await session.get(ExternalPublicationModel, UUID(pubs[0]))
            pub.external_id = "7:offer" if platform == "rozetka" else "101"
            pub.resource_type = "source_offer" if platform == "rozetka" else "product"
            pub.platform_data = (
                {"item_id": 9, "rz_item_id": 42, "sync_source_id": 7}
                if platform == "rozetka"
                else {}
            )
            pub.raw_data = {"name": "Content must survive", "stock_quantity": 3}
            pub.normalized_data = {
                **pub.normalized_data,
                "quantity": "3",
                "stock_mode": "own",
            }
            await session.commit()
        payload, preview = await self.propose(channel, root, [root], pubs)
        body = {k: v for k, v in payload.items() if k != "group_id"} | {
            "catalog_token": preview["catalog_token"],
            "publication_token": preview["publication_token"],
        }
        group = (
            await self.call("POST", f"/channels/{channel}/catalog-bindings", body, 201)
        )["id"]
        return channel, group, root, pubs[0]

    async def stock_job(self, kind: str = "channels.sync_stock"):
        async with self.sessions() as session:
            rows = await SqlAlchemyScheduledJobRepository(session).claim_due_jobs(
                limit=100,
                now=datetime.now(UTC),
                locked_until=datetime.now(UTC) + timedelta(minutes=5),
                lock_token=str(uuid4()),
            )
            await session.commit()
        self.claimed_jobs.extend(rows)
        found = next(v for v in self.claimed_jobs if v.job_type == kind)
        self.claimed_jobs.remove(found)
        return found

    async def finish(self, job) -> None:
        async with self.sessions() as session:
            await SqlAlchemyScheduledJobRepository(session).mark_done(
                job_id=job.id, lock_token=job.lock_token, completed_at=datetime.now(UTC)
            )
            await session.commit()

    async def enable(self, channel: str, allowed: bool = True) -> dict:
        before = await self.detail(channel)
        await self.call(
            "PATCH",
            f"/channels/{channel}",
            {
                "expected_revision": before["revision"],
                "config": {
                    **before["config"],
                    "settings": {
                        **before["config"]["settings"],
                        "stock_sync": {"allow_export": allowed},
                    },
                },
            },
        )
        return await self.detail(channel)

    async def stock_state(self, channel: str, group: str) -> dict:
        return await self.call(
            "GET", f"/channels/{channel}/catalog-bindings/{group}/stock"
        )

    async def test_prom_retry_empty_ack_completes_after_confirmed_readback(
        self,
    ) -> None:
        """Повтор после отказа сохраняет новое подтверждение и не повторяет завершённую запись."""
        channel, group, root, publication = await self.setup_stock(platform="prom")
        await self.enable(channel)
        url = f"/channels/{channel}/catalog-bindings/{group}/stock-export"
        await self.call("POST", url, {}, 202)
        rejected_job = await self.stock_job()
        before = {
            "product": {"id": 101, "quantity_in_stock": 3, "presence": "available"}
        }
        rejected_http = FixtureHttp(
            [
                before,
                before,
                {
                    "processed_ids": [],
                    "errors": {
                        "101": {
                            "code": "stock_read_only",
                            "message": "private provider text",
                        }
                    },
                },
            ]
        )
        await ChannelsStockJobHandler(
            self.sessions,
            platforms=InstalledPlatforms(rejected_http),
            cipher=self.cipher,
        ).handle(rejected_job)
        await self.finish(rejected_job)
        failed = await self.stock_state(channel, group)
        self.assertEqual(failed["items"][0]["operation"]["status"], "failed")
        self.assertEqual(
            failed["items"][0]["operation"]["error_code"], "stock_write_rejected"
        )

        accepted = await self.call("POST", url, {}, 202)
        retry = await self.stock_job()
        self.assertNotEqual(accepted["operation_ids"], [str(rejected_job.id)])
        after = {
            "product": {"id": 101, "quantity_in_stock": 7, "presence": "available"}
        }
        acknowledgement = json.loads(
            (
                Path(__file__).parent
                / "fixtures/channels/prom-stock-update-unchanged.json"
            ).read_text()
        )
        http = FixtureHttp([after, after, acknowledgement, after])
        worker = ChannelsStockJobHandler(
            self.sessions, platforms=InstalledPlatforms(http), cipher=self.cipher
        )
        with self.assertLogs(
            "src.modules.channels.presentation.stock_sync.jobs", level="INFO"
        ) as logs:
            await worker.handle(retry)
        committed = next(
            record
            for record in logs.records
            if getattr(record, "event", None) == "channels.stock.step_committed"
        )
        self.assertEqual(committed.publication_id, publication)
        self.assertEqual(committed.job_id, str(retry.id))
        self.assertIsNone(committed.reason_code)
        await worker.handle(retry)
        await self.finish(retry)
        self.assertEqual(
            [call[0] for call in http.calls], ["GET", "GET", "POST", "GET"]
        )
        state = await self.stock_state(channel, group)
        operation = state["items"][0]["operation"]
        self.assertEqual(operation["status"], "completed")
        self.assertIsNone(operation["error_code"])
        self.assertEqual(state["items"][0]["publication_quantity"], "7")
        self.assertEqual(
            (await self.call("GET", f"/catalog/items/{root}?locale=uk"))["item"][
                "stock"
            ]["stock_quantity"],
            7,
        )
        source = (await self.rows(ExternalPublicationModel))[0]
        self.assertEqual(
            source["raw_data"], {"name": "Content must survive", "stock_quantity": 3}
        )

    async def test_stock_settings_are_json_only_and_public_metadata_is_rejected(
        self,
    ) -> None:
        """Проверяет контракт трёх платформ без повторной проверки и лишних заданий."""
        for platform in ("prom", "rozetka", "woocommerce"):
            channel, group, root, publication = await self.setup_stock(
                platform=platform
            )
            before = await self.detail(channel)
            jobs_before = await self.rows(ScheduledJobModel)
            enabled = await self.enable(channel)
            self.assertNotIn("allow_stock_export", enabled)
            self.assertEqual(
                enabled["config"]["settings"]["stock_sync"], {"allow_export": True}
            )
            self.assertEqual(enabled["revision"], before["revision"] + 1)
            self.assertEqual(enabled["config_revision"], before["config_revision"])
            self.assertEqual(enabled["verification"], before["verification"])
            self.assertIn("write_stock", enabled["available_capabilities"])
            self.assertEqual(jobs_before, await self.rows(ScheduledJobModel))
            saved = next(
                v
                for v in await self.rows(ConnectionModel)
                if str(v["channel_id"]) == channel
            )
            self.assertTrue(saved["settings"]["stock_sync"]["allow_export"])
            self.assertEqual(saved["settings"]["stock_sync"]["revision"], 2)
            self.assertIsInstance(saved["settings"]["stock_sync"]["changed_at"], str)
            for extra in (
                {"revision": 99},
                {"changed_at": datetime.now(UTC).isoformat()},
                {"allow_export": "false"},
            ):
                await self.call(
                    "PATCH",
                    f"/channels/{channel}",
                    {
                        "expected_revision": enabled["revision"],
                        "config": {
                            **enabled["config"],
                            "settings": {
                                **enabled["config"]["settings"],
                                "stock_sync": {"allow_export": True, **extra},
                            },
                        },
                    },
                    422,
                )
                self.assertEqual(
                    (await self.detail(channel))["revision"], enabled["revision"]
                )
            await self.call(
                "PATCH",
                f"/channels/{channel}",
                {"expected_revision": enabled["revision"], "allow_stock_export": False},
                422,
            )
            repeated = await self.enable(channel)
            self.assertEqual(repeated["revision"], enabled["revision"])
            await self.call(
                "PATCH",
                f"/channels/{channel}",
                {"expected_revision": enabled["revision"], "name": "Renamed"},
            )
            renamed = await self.detail(channel)
            self.assertEqual(
                renamed["config"]["settings"]["stock_sync"], {"allow_export": True}
            )
            self.assertEqual(renamed["config_revision"], before["config_revision"])

    async def test_stock_refresh_only_publication_and_auto_export_outbox_worker(
        self,
    ) -> None:
        channel, group, root, pub = await self.setup_stock()
        before = await self.detail(channel)
        self.assertFalse(before["config"]["settings"]["stock_sync"]["allow_export"])
        await self.call(
            "POST",
            f"/channels/{channel}/catalog-bindings/{group}/stock-export",
            {},
            403,
        )
        accepted = await self.call(
            "POST",
            f"/channels/{channel}/catalog-bindings/{group}/stock-import",
            {},
            202,
        )
        http = FixtureHttp(
            [
                {
                    "id": 101,
                    "manage_stock": True,
                    "stock_quantity": 4,
                    "stock_status": "instock",
                    "backorders": "no",
                }
            ]
        )
        job = await self.stock_job()
        worker = ChannelsStockJobHandler(
            self.sessions, platforms=InstalledPlatforms(http), cipher=self.cipher
        )
        await worker.handle(job)
        await worker.handle(job)
        await self.finish(job)
        self.assertEqual(len(http.calls), 1)
        catalog = await self.call("GET", f"/catalog/items/{root}?locale=uk")
        self.assertEqual(catalog["item"]["stock"]["stock_quantity"], 7)
        source = (await self.rows(ExternalPublicationModel))[0]
        self.assertEqual(source["normalized_data"]["quantity"], "4")
        self.assertEqual(
            source["raw_data"], {"name": "Content must survive", "stock_quantity": 3}
        )
        self.assertEqual(
            len(
                [
                    v
                    for v in await self.rows(ScheduledJobModel)
                    if v["job_type"] == "catalog.stock_changed"
                ]
            ),
            0,
        )
        state = await self.stock_state(channel, group)
        self.assertEqual(state["items"][0]["operation"]["status"], "completed")
        self.assertEqual(state["items"][0]["publication_quantity"], "4")
        enabled = await self.enable(channel)
        self.assertEqual(enabled["config_revision"], before["config_revision"])
        self.assertEqual(enabled["verification"], before["verification"])
        await self.call(
            "PATCH",
            f"/catalog/items/{root}",
            {
                "stock": {
                    "manage_stock": True,
                    "stock_quantity": 8,
                    "stock_status": None,
                    "backorders": "no",
                }
            },
        )
        event_job = await self.stock_job("catalog.stock_changed")
        consumer = ChannelsCatalogStockChangedJobHandler(self.sessions)
        await consumer.handle(event_job)
        await consumer.handle(event_job)
        await self.finish(event_job)
        after = {
            "id": 101,
            "manage_stock": True,
            "stock_quantity": 8,
            "stock_status": "instock",
            "backorders": "no",
        }
        http = FixtureHttp([{**after, "stock_quantity": 4}, after, after])
        write_job = await self.stock_job()
        await ChannelsStockJobHandler(
            self.sessions, platforms=InstalledPlatforms(http), cipher=self.cipher
        ).handle(write_job)
        await self.finish(write_job)
        self.assertEqual(
            http.calls[1][2]["body"],
            {"manage_stock": True, "stock_quantity": 8, "backorders": "no"},
        )
        self.assertEqual(
            (await self.stock_state(channel, group))["items"][0]["operation"]["status"],
            "completed",
        )
        async with self.sessions() as session:
            self.assertEqual(
                len(
                    (
                        await session.scalars(
                            select(IntegrationOutboxEventModel).where(
                                IntegrationOutboxEventModel.tenant_id == self.tenant
                            )
                        )
                    ).all()
                ),
                1,
            )
            self.assertEqual(
                len(
                    (
                        await session.scalars(
                            select(IntegrationInboxEventModel).where(
                                IntegrationInboxEventModel.tenant_id == self.tenant
                            )
                        )
                    ).all()
                ),
                1,
            )

    async def test_stock_policy_generation_unlink_and_missing_quantity_guards(
        self,
    ) -> None:
        channel, group, root, pub = await self.setup_stock(tracked=False)
        await self.enable(channel)
        state = await self.stock_state(channel, group)
        self.assertEqual(state["items"][0]["export_blocker"], "stock_tracking_required")
        await self.call(
            "POST",
            f"/channels/{channel}/catalog-bindings/{group}/stock-export",
            {},
            422,
        )
        await self.call(
            "PATCH",
            f"/catalog/items/{root}",
            {
                "stock": {
                    "manage_stock": True,
                    "stock_quantity": 2,
                    "stock_status": None,
                    "backorders": "no",
                }
            },
        )
        accepted = await self.call(
            "POST",
            f"/channels/{channel}/catalog-bindings/{group}/stock-export",
            {},
            202,
        )
        job = await self.stock_job()
        await self.enable(channel, False)
        await self.enable(channel, True)
        http = FixtureHttp([])
        await ChannelsStockJobHandler(
            self.sessions, platforms=InstalledPlatforms(http), cipher=self.cipher
        ).handle(job)
        self.assertEqual(http.calls, [])
        self.assertEqual(
            (await self.stock_state(channel, group))["items"][0]["operation"]["status"],
            "cancelled",
        )
        # Старое событие Catalog также не отправляется после выключения/включения.
        event_job = await self.stock_job("catalog.stock_changed")
        await ChannelsCatalogStockChangedJobHandler(self.sessions).handle(event_job)
        await self.finish(event_job)
        self.assertEqual(
            (await self.stock_state(channel, group))["items"][0]["operation"]["status"],
            "cancelled",
        )
        await self.finish(job)
        await self.call(
            "POST",
            f"/channels/{channel}/catalog-bindings/{group}/stock-export",
            {},
            202,
        )
        stale = await self.stock_job()
        detail = await self.call(
            "GET", f"/channels/{channel}/catalog-bindings/{group}?locale=uk"
        )
        await self.call(
            "DELETE",
            f"/channels/{channel}/catalog-bindings/{group}?expected_revision={detail['binding']['group']['revision']}",
            status=204,
        )
        await ChannelsStockJobHandler(
            self.sessions, platforms=InstalledPlatforms(http), cipher=self.cipher
        ).handle(stale)
        self.assertEqual(http.calls, [])

    async def test_stock_lease_loss_does_not_apply_observation(self) -> None:
        channel, group, root, pub = await self.setup_stock()
        await self.call(
            "POST",
            f"/channels/{channel}/catalog-bindings/{group}/stock-import",
            {},
            202,
        )
        job = await self.stock_job()
        outer = self

        class LostLeaseHttp(FixtureHttp):
            async def request(self, method, url, **kwargs):
                async with outer.sessions() as session:
                    await session.execute(
                        update(ScheduledJobModel)
                        .where(ScheduledJobModel.id == job.id)
                        .values(lock_token="other-worker")
                    )
                    await session.commit()
                return await super().request(method, url, **kwargs)

        http = LostLeaseHttp([{"id": 101, "manage_stock": True, "stock_quantity": 90}])
        await ChannelsStockJobHandler(
            self.sessions, platforms=InstalledPlatforms(http), cipher=self.cipher
        ).handle(job)
        self.assertEqual(
            (await self.rows(ExternalPublicationModel))[0]["normalized_data"][
                "quantity"
            ],
            "3",
        )
        self.assertEqual(
            (await self.call("GET", f"/catalog/items/{root}?locale=uk"))["item"][
                "stock"
            ]["stock_quantity"],
            7,
        )

    async def setup_shared_stock(
        self, *, catalog_shared: bool, platform_shared: bool
    ) -> tuple[str, str, str, list[str]]:
        from copy import deepcopy

        root, positions = await self.catalog(variable=True)
        channel, pubs = await self.source(platform="woocommerce", variable=True)
        child2 = uuid4()
        async with self.sessions() as session:
            await bind_tenant_schema(
                await session.connection(), self.tenant, self.naming
            )
            repository = SqlAlchemyChannelRepository(session, self.tenant)
            aggregate = await repository.get(EntityIdVO(UUID(channel)), for_update=True)
            aggregate.apply_verification(
                job_id=aggregate.connection.verification.job_id,
                config_revision=1,
                identity=ResourceIdentityVO(namespace="test.stock", key=str(uuid4())),
                error_code=None,
                now=datetime.now(UTC),
            )
            await repository.save(aggregate)
            parent = await session.get(ExternalPublicationModel, UUID(pubs[0]))
            child = await session.get(ExternalPublicationModel, UUID(pubs[1]))
            parent.external_id = "100"
            parent.normalized_data = {
                **parent.normalized_data,
                "quantity": "3" if platform_shared else None,
                "stock_mode": "own" if platform_shared else "untracked",
            }
            child.external_id = "101"
            child.resource_type = "variation"
            child.platform_data = {"parent_product_id": "100"}
            child.normalized_data = {
                **child.normalized_data,
                "quantity": None if platform_shared else "3",
                "stock_mode": "parent" if platform_shared else "own",
            }
            await session.flush()
            values = {
                c.name: deepcopy(getattr(child, c.name))
                for c in ExternalPublicationModel.__table__.columns
            }
            values.update(id=child2, external_id="102")
            session.add(ExternalPublicationModel(**values))
            await session.commit()
        if catalog_shared:
            await self.call(
                "PATCH",
                f"/catalog/items/{root}",
                {
                    "stock": {
                        "manage_stock": True,
                        "stock_quantity": 7,
                        "stock_status": None,
                        "backorders": "no",
                    }
                },
            )
        else:
            for pos in positions:
                await self.call(
                    "PATCH",
                    f"/catalog/items/{root}/variants/{pos}",
                    {
                        "stock": {
                            "manage_stock": True,
                            "stock_quantity": 7,
                            "stock_status": None,
                            "backorders": "no",
                        }
                    },
                )
        children = [pubs[1], str(child2)]
        payload, preview = await self.propose(
            channel,
            root,
            positions,
            children,
            mode="VARIABLE_TO_VARIABLE",
            source_root=pubs[0],
        )
        body = {k: v for k, v in payload.items() if k != "group_id"} | {
            "catalog_token": preview["catalog_token"],
            "publication_token": preview["publication_token"],
        }
        group = (
            await self.call("POST", f"/channels/{channel}/catalog-bindings", body, 201)
        )["id"]
        await self.enable(channel)
        return channel, group, root, children

    async def test_stock_shared_woo_pool_writes_parent_once(self) -> None:
        channel, group, root, children = await self.setup_shared_stock(
            catalog_shared=True, platform_shared=True
        )
        accepted = await self.call(
            "POST",
            f"/channels/{channel}/catalog-bindings/{group}/stock-export",
            {},
            202,
        )
        self.assertEqual(len(accepted["operation_ids"]), 1)
        job = await self.stock_job()
        parent = {
            "id": 100,
            "manage_stock": True,
            "stock_quantity": 3,
            "backorders": "no",
            "stock_status": "instock",
        }
        after = {**parent, "stock_quantity": 7}
        http = FixtureHttp(
            [
                {"id": 101, "manage_stock": "parent", "stock_quantity": None},
                parent,
                after,
                after,
            ]
        )
        await ChannelsStockJobHandler(
            self.sessions, platforms=InstalledPlatforms(http), cipher=self.cipher
        ).handle(job)
        self.assertEqual([v[0] for v in http.calls], ["GET", "GET", "PUT", "GET"])
        self.assertTrue(http.calls[2][1].endswith("/products/100"))
        state = await self.stock_state(channel, group)
        self.assertEqual(
            [v["publication_quantity"] for v in state["items"]], ["7", "7"]
        )
        self.assertEqual(
            len({v["operation"]["operation_id"] for v in state["items"]}), 1
        )

    async def test_stock_ambiguous_pool_mappings_block_before_queue(self) -> None:
        for catalog_shared, platform_shared in [(True, False), (False, True)]:
            channel, group, root, children = await self.setup_shared_stock(
                catalog_shared=catalog_shared, platform_shared=platform_shared
            )
            state = await self.stock_state(channel, group)
            self.assertEqual(
                {v["export_blocker"] for v in state["items"]},
                {"stock_ownership_ambiguous"},
            )
            response = await self.call(
                "POST",
                f"/channels/{channel}/catalog-bindings/{group}/stock-export",
                {},
                422,
            )
            self.assertEqual(response["detail"]["code"], "stock_ownership_ambiguous")

    async def test_stock_rozetka_duplicate_marketplace_target_blocks_export(
        self,
    ) -> None:
        channel, group, root, publication = await self.setup_stock(platform="rozetka")
        _, other_publications = await self.source(
            platform="rozetka", existing_channel=channel
        )
        async with self.sessions() as session:
            await bind_tenant_schema(
                await session.connection(), self.tenant, self.naming
            )
            other = await session.get(
                ExternalPublicationModel, UUID(other_publications[0])
            )
            other.external_id = "8:other-offer"
            other.resource_type = "source_offer"
            other.platform_data = {
                "item_id": 10,
                "rz_item_id": 42,
                "sync_source_id": 8,
            }
            other.normalized_data = {
                **other.normalized_data,
                "quantity": "3",
                "stock_mode": "own",
            }
            await session.commit()
        payload, preview = await self.propose(channel, root, [root], other_publications)
        body = {k: v for k, v in payload.items() if k != "group_id"} | {
            "catalog_token": preview["catalog_token"],
            "publication_token": preview["publication_token"],
        }
        await self.call("POST", f"/channels/{channel}/catalog-bindings", body, 201)
        await self.enable(channel)
        state = await self.stock_state(channel, group)
        self.assertEqual(
            state["items"][0]["export_blocker"], "stock_ownership_ambiguous"
        )
        response = await self.call(
            "POST",
            f"/channels/{channel}/catalog-bindings/{group}/stock-export",
            {},
            422,
        )
        self.assertEqual(response["detail"]["code"], "stock_ownership_ambiguous")

    async def test_stock_latest_catalog_quantity_used_before_api_write(self) -> None:
        channel, group, root, pub = await self.setup_stock()
        await self.enable(channel)
        await self.call(
            "POST",
            f"/channels/{channel}/catalog-bindings/{group}/stock-export",
            {},
            202,
        )
        job = await self.stock_job()
        outer = self

        class ChangingCatalogHttp(FixtureHttp):
            async def request(self, method, url, **kwargs):
                if not self.calls:
                    await outer.call(
                        "PATCH",
                        f"/catalog/items/{root}",
                        {
                            "stock": {
                                "manage_stock": True,
                                "stock_quantity": 11,
                                "stock_status": None,
                                "backorders": "no",
                            }
                        },
                    )
                return await super().request(method, url, **kwargs)

        before = {
            "id": 101,
            "manage_stock": True,
            "stock_quantity": 3,
            "backorders": "no",
        }
        after = {**before, "stock_quantity": 11}
        http = ChangingCatalogHttp([before, after, after])
        await ChannelsStockJobHandler(
            self.sessions, platforms=InstalledPlatforms(http), cipher=self.cipher
        ).handle(job)
        self.assertEqual(http.calls[1][2]["body"]["stock_quantity"], 11)
        self.assertEqual(
            (await self.stock_state(channel, group))["items"][0]["operation"]["status"],
            "completed",
        )

    async def test_stock_change_during_write_queues_correction(self) -> None:
        channel, group, root, pub = await self.setup_stock()
        await self.enable(channel)
        await self.call(
            "POST",
            f"/channels/{channel}/catalog-bindings/{group}/stock-export",
            {},
            202,
        )
        job = await self.stock_job()
        outer = self

        class ChangingCatalogHttp(FixtureHttp):
            async def request(self, method, url, **kwargs):
                if method == "PUT":
                    await outer.call(
                        "PATCH",
                        f"/catalog/items/{root}",
                        {
                            "stock": {
                                "manage_stock": True,
                                "stock_quantity": 12,
                                "stock_status": None,
                                "backorders": "no",
                            }
                        },
                    )
                return await super().request(method, url, **kwargs)

        before = {
            "id": 101,
            "manage_stock": True,
            "stock_quantity": 3,
            "backorders": "no",
        }
        after = {**before, "stock_quantity": 7}
        http = ChangingCatalogHttp([before, after, after])
        await ChannelsStockJobHandler(
            self.sessions, platforms=InstalledPlatforms(http), cipher=self.cipher
        ).handle(job)
        state = await self.stock_state(channel, group)
        self.assertEqual(state["items"][0]["publication_quantity"], "7")
        self.assertEqual(state["items"][0]["catalog_quantity"], 12)
        self.assertEqual(state["items"][0]["operation"]["status"], "queued")
        self.assertNotEqual(state["items"][0]["operation"]["operation_id"], str(job.id))

    async def test_stock_migration_roundtrip_preserves_catalog_and_disables_export(
        self,
    ) -> None:
        from src.modules.tenancy.infrastructure.tenant.persistence.tenant_migrations import (
            TenantMigrator,
        )
        from sqlalchemy import text

        channel, group, root, pub = await self.setup_stock()
        await self.enable(channel)
        platform_settings = (await self.detail(channel))["config"]["settings"].copy()
        platform_settings.pop("stock_sync")
        async with self.engine.begin() as connection:
            await TenantMigrator().downgrade(
                connection, self.schemas[0], "0009_channels_catalog_bindings"
            )
            await TenantMigrator().upgrade(connection, self.schemas[0])
            revision = await connection.scalar(
                text(f'SELECT version_num FROM "{self.schemas[0]}".alembic_version')
            )
            columns = set(
                await connection.scalars(
                    text(
                        "SELECT column_name FROM information_schema.columns WHERE table_schema=:schema AND table_name='channels'"
                    ),
                    {"schema": self.schemas[0]},
                )
            )
            self.assertFalse(
                {
                    "allow_stock_export",
                    "stock_policy_revision",
                    "stock_policy_changed_at",
                }
                & columns
            )
        self.assertEqual(revision, "0010_channels_stock_sync")
        settings = (await self.detail(channel))["config"]["settings"].copy()
        settings.pop("stock_sync")
        self.assertEqual(settings, platform_settings)
        self.assertFalse(
            (await self.detail(channel))["config"]["settings"]["stock_sync"][
                "allow_export"
            ]
        )
        self.assertEqual(
            (await self.call("GET", f"/catalog/items/{root}?locale=uk"))["item"][
                "stock"
            ]["stock_quantity"],
            7,
        )

    async def test_stock_schedule_failure_rolls_back_state(self) -> None:
        channel, group, root, pub = await self.setup_stock()
        with patch(
            "src.modules.channels.infrastructure.stock_sync.jobs.SharedStockJobs.schedule",
            side_effect=RuntimeError("test scheduler unavailable"),
        ):
            with self.assertRaisesRegex(RuntimeError, "test scheduler unavailable"):
                await self.call(
                    "POST",
                    f"/channels/{channel}/catalog-bindings/{group}/stock-import",
                    {},
                    202,
                )
        self.assertEqual(await self.rows(StockSyncModel), [])
        self.assertFalse(
            any(
                v["job_type"] == "channels.sync_stock"
                for v in await self.rows(ScheduledJobModel)
            )
        )

    async def test_stock_permission_change_waits_for_started_operation(self) -> None:
        channel, group, root, pub = await self.setup_stock()
        await self.enable(channel)
        await self.call(
            "POST",
            f"/channels/{channel}/catalog-bindings/{group}/stock-export",
            {},
            202,
        )
        job = await self.stock_job()
        started, release = asyncio.Event(), asyncio.Event()

        class PausedHttp(FixtureHttp):
            async def request(self, method, url, **kwargs):
                if not self.calls:
                    started.set()
                    await release.wait()
                return await super().request(method, url, **kwargs)

        before = {
            "id": 101,
            "manage_stock": True,
            "stock_quantity": 3,
            "backorders": "no",
        }
        after = {**before, "stock_quantity": 7}
        http = PausedHttp([before, after, after])
        worker = asyncio.create_task(
            ChannelsStockJobHandler(
                self.sessions, platforms=InstalledPlatforms(http), cipher=self.cipher
            ).handle(job)
        )
        await asyncio.wait_for(started.wait(), 5)
        disable = asyncio.create_task(self.enable(channel, False))
        try:
            await asyncio.sleep(0.05)
            self.assertFalse(disable.done())
        finally:
            release.set()
        await asyncio.wait_for(worker, 10)
        await asyncio.wait_for(disable, 10)
        self.assertFalse(
            (await self.detail(channel))["config"]["settings"]["stock_sync"][
                "allow_export"
            ]
        )
        self.assertEqual(len([v for v in http.calls if v[0] == "PUT"]), 1)
        await self.call(
            "POST",
            f"/channels/{channel}/catalog-bindings/{group}/stock-export",
            {},
            403,
        )
