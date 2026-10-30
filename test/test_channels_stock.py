"""Доменные ограничения и точные контракты количественного API трёх площадок."""

from dataclasses import fields, replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
import json
from pathlib import Path
import unittest
from uuid import uuid4
from unittest.mock import AsyncMock
from pydantic import ValidationError

from test.test_channels import FixtureHttp
from test import test_channels_domain as channel_domain_support
from src.modules.channels.application.external_publication.catalog_details import (
    PublicationLookup,
)
from src.modules.channels.application.error import VerificationFailure
from src.modules.channels.domain.stock_sync.aggregate import StockSync
from src.modules.channels.domain.stock_sync.error import StockSyncError
from src.modules.channels.domain.stock_sync.value_object import (
    StockSnapshotVO,
    StockLinkFacts,
    StockOwnershipPolicy,
)
from src.modules.channels.infrastructure.registry import InstalledPlatforms
from src.modules.channels.domain.channel.value_object.connection_config import (
    ConnectionConfigVO,
)
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.catalog.domain.catalog_item.value_object.stock import (
    StockSpecificationVO,
    BackorderPolicy,
)
from src.modules.catalog.domain.catalog_item.aggregate import CatalogItem
from src.modules.catalog.domain.catalog_item.value_object.identifier import (
    CatalogItemIdVO,
)


def identifier() -> EntityIdVO:
    return EntityIdVO(uuid4())


def lookup(
    resource: str = "product",
    external: str = "101",
    parent: bool = False,
    native: dict | None = None,
) -> PublicationLookup:
    return PublicationLookup(
        uuid4(),
        resource,
        external,
        "variant" if parent else "simple",
        uuid4() if parent else None,
        1,
        native or {},
    )


class StockDomainTests(unittest.TestCase):
    def state(self, direction: str = "read") -> StockSync:
        return StockSync.create(
            publication_id=identifier(),
            connection_id=identifier(),
            operation_id=identifier(),
            direction=direction,
            config_revision=1,
            policy_revision=1,
            binding_group_id=identifier(),
            binding_revision=1,
            now=datetime.now(UTC),
        )

    def test_unknown_is_not_zero_and_documents_are_exact(self) -> None:
        unknown = StockSnapshotVO("product", "1", "unknown", None, None)
        zero = StockSnapshotVO("product", "1", "own", Decimal(0), "out_of_stock")
        self.assertIsNone(unknown.to_document()["quantity"])
        self.assertEqual(zero.to_document()["quantity"], "0")
        for quantity in (1, Decimal("NaN"), Decimal("Infinity")):
            with self.assertRaises(StockSyncError):
                StockSnapshotVO("product", "1", "own", quantity, None)

    def test_old_and_duplicate_jobs_do_not_apply(self) -> None:
        state = self.state()
        now = datetime.now(UTC)
        self.assertFalse(state.start(operation_id=identifier(), quantity=None, now=now))
        state.start(operation_id=state.operation_id, quantity=None, now=now)
        result = StockSnapshotVO("product", "101", "own", Decimal(4), "in_stock")
        self.assertFalse(
            state.complete(
                operation_id=identifier(), snapshot=result, error_code=None, now=now
            )
        )
        self.assertTrue(
            state.complete(
                operation_id=state.operation_id,
                snapshot=result,
                error_code=None,
                now=now,
            )
        )
        self.assertFalse(
            state.complete(
                operation_id=state.operation_id,
                snapshot=result,
                error_code=None,
                now=now,
            )
        )
        self.assertFalse(
            state.start(operation_id=state.operation_id, quantity=None, now=now)
        )

    def test_error_preserves_last_observation_and_retry_gets_new_generation(
        self,
    ) -> None:
        state = self.state()
        now = datetime.now(UTC)
        state.start(operation_id=state.operation_id, quantity=None, now=now)
        observed = StockSnapshotVO("product", "101", "own", Decimal(5), "in_stock")
        state.complete(
            operation_id=state.operation_id, snapshot=observed, error_code=None, now=now
        )
        previous = state.operation_id
        state.request(
            operation_id=identifier(),
            direction="write",
            config_revision=1,
            policy_revision=1,
            binding_group_id=state.binding_group_id,
            binding_revision=1,
            now=now,
        )
        state.start(operation_id=state.operation_id, quantity=8, now=now)
        state.complete(
            operation_id=state.operation_id,
            snapshot=None,
            error_code="permission_missing",
            now=now,
        )
        self.assertEqual(state.observed.quantity, 5)
        self.assertNotEqual(state.operation_id, previous)
        self.assertEqual(state.status, "failed")

    def test_restore_rejects_contradictions(self) -> None:
        state = self.state()
        values = {f.name: getattr(state, f.name) for f in fields(state)}
        for changes in (
            {"revision": 0},
            {"config_revision": 0},
            {"status": "completed"},
            {"observed_at": datetime.now(UTC)},
            {"status": "failed"},
            {"error_code": "error"},
            {"desired_quantity": 1},
            {"updated_at": datetime.now()},
        ):
            with self.subTest(changes=changes), self.assertRaises(StockSyncError):
                StockSync.restore(**(values | changes))

    def test_invalid_request_is_atomic(self) -> None:
        state = self.state()
        before = replace(state)
        with self.assertRaises(StockSyncError):
            state.request(
                operation_id=identifier(),
                direction="invalid",
                config_revision=1,
                policy_revision=1,
                binding_group_id=state.binding_group_id,
                binding_revision=1,
                now=datetime.now(UTC),
            )
        self.assertEqual(state, before)
        with self.assertRaises(StockSyncError):
            state.start(
                operation_id=state.operation_id, quantity=5, now=datetime.now(UTC)
            )
        self.assertEqual(state, before)
        state.start(
            operation_id=state.operation_id, quantity=None, now=datetime.now(UTC)
        )
        before = replace(state)
        for error in ("", "   ", 1):
            with self.subTest(error=error), self.assertRaises(StockSyncError):
                state.complete(
                    operation_id=state.operation_id,
                    snapshot=None,
                    error_code=error,
                    now=datetime.now(UTC),
                )
            self.assertEqual(state, before)

    def test_inventory_ownership_is_not_inferred_from_equal_numbers(self) -> None:
        catalog, position_a, position_b, remote_a, remote_b = tuple(
            identifier() for _ in range(5)
        )
        a = StockLinkFacts(identifier(), remote_a, position_a, catalog, 10, "no")
        b = StockLinkFacts(identifier(), remote_b, position_b, catalog, 10, "no")
        policy = StockOwnershipPolicy()
        with self.assertRaisesRegex(StockSyncError, "stock_ownership_ambiguous"):
            policy.ensure_exportable(a, (a, b))
        shared_b = replace(b, platform_owner_id=remote_a)
        policy.ensure_exportable(a, (a, shared_b))
        with self.assertRaisesRegex(StockSyncError, "stock_ownership_ambiguous"):
            policy.ensure_exportable(
                a, (a, replace(shared_b, catalog_owner_id=position_b))
            )
        policy.ensure_exportable(
            replace(a, catalog_owner_id=position_a),
            (
                replace(a, catalog_owner_id=position_a),
                replace(b, catalog_owner_id=position_b),
            ),
        )

    def test_manual_and_negative_catalog_stock_cannot_export(self) -> None:
        a = StockLinkFacts(
            identifier(), identifier(), identifier(), identifier(), None, "no"
        )
        with self.assertRaisesRegex(StockSyncError, "stock_tracking_required"):
            StockOwnershipPolicy().ensure_exportable(a, (a,))
        with self.assertRaisesRegex(StockSyncError, "stock_negative_unsupported"):
            StockOwnershipPolicy().ensure_exportable(replace(a, quantity=-2), (a,))

    def test_channel_policy_changes_revision_once_without_reverification(self) -> None:
        setup = channel_domain_support.ChannelsDomainTests()
        setup.setUp()
        channel = setup.channel
        revision = channel.revision
        config_revision = channel.connection.config_revision
        job = channel.connection.verification.job_id
        changed = channel.change_settings(
            expected_revision=revision,
            name=None,
            config=None,
            encrypted_credentials=None,
            job_id=identifier(),
            actor_id=setup.actor,
            now=setup.now,
            allow_export=True,
        )
        self.assertFalse(changed)
        self.assertTrue(channel.connection.stock_sync.allow_export)
        self.assertEqual(channel.revision, revision + 1)
        self.assertEqual(channel.connection.stock_sync.revision, 2)
        self.assertEqual(channel.connection.config_revision, config_revision)
        self.assertEqual(channel.connection.verification.job_id, job)
        channel.change_settings(
            expected_revision=channel.revision,
            name=None,
            config=None,
            encrypted_credentials=None,
            job_id=identifier(),
            actor_id=setup.actor,
            now=setup.now,
            allow_export=True,
        )
        self.assertEqual(channel.revision, revision + 1)
        self.assertEqual(channel.connection.stock_sync.revision, 2)

    def test_catalog_event_only_for_quantitative_changes(self) -> None:
        now = datetime.now(UTC)
        actor = identifier()
        item = CatalogItem.create(CatalogItemIdVO(uuid4()), actor, now, identifier())
        item.update(
            fields=frozenset({"stock"}),
            actor=actor,
            now=now,
            stock=StockSpecificationVO(True, 7, None, BackorderPolicy.NO),
        )
        self.assertEqual(len(item.pull_stock_events()), 1)
        item.update(fields=frozenset({"stock"}), actor=actor, now=now, stock=item.stock)
        self.assertEqual(item.pull_stock_events(), ())
        item.update(fields=frozenset({"virtual"}), actor=actor, now=now, virtual=True)
        self.assertEqual(item.pull_stock_events(), ())

    def test_full_sync_started_before_stock_observation_keeps_new_quantity(
        self,
    ) -> None:
        from src.modules.channels.domain.external_publication.aggregate import (
            ExternalPublication,
        )
        from src.modules.channels.domain.external_publication.value_object import (
            PublicationData,
            PublicationKind,
        )

        now = datetime.now(UTC)
        publication = ExternalPublication.create(
            publication_id=identifier(),
            connection_id=identifier(),
            resource_type="product",
            external_id="101",
            kind=PublicationKind.SIMPLE,
            parent_id=None,
            raw_data={"name": "Original", "stock_quantity": 2},
            data=PublicationData((), "UAH", quantity=Decimal(2), stock_mode="own"),
            platform_schema="test.v1",
            platform_data={},
            run_id=identifier(),
            now=now,
        )
        publication.observe_stock(
            quantity=Decimal(9),
            stock_mode="own",
            availability="in_stock",
            native={"config_revision": 1},
            now=now + timedelta(seconds=2),
        )
        publication.observe(
            kind=PublicationKind.SIMPLE,
            parent_id=None,
            raw_data={"name": "Fresh content", "stock_quantity": 2},
            data=PublicationData((), "UAH", quantity=Decimal(2), stock_mode="own"),
            platform_schema="test.v1",
            platform_data={},
            run_id=identifier(),
            now=now + timedelta(seconds=3),
            source_started_at=now + timedelta(seconds=1),
            config_revision=1,
        )
        self.assertEqual(publication.data.quantity, 9)
        self.assertEqual(publication.raw_data["name"], "Fresh content")
        self.assertIn("stock_observation", publication.platform_data)
        publication.observe(
            kind=PublicationKind.SIMPLE,
            parent_id=None,
            raw_data={"stock_quantity": 5},
            data=PublicationData((), "UAH", quantity=Decimal(5), stock_mode="own"),
            platform_schema="test.v1",
            platform_data={},
            run_id=identifier(),
            now=now + timedelta(seconds=5),
            source_started_at=now + timedelta(seconds=4),
            config_revision=1,
        )
        self.assertEqual(publication.data.quantity, 5)

    def test_stock_state_rejects_other_config_policy_and_connection(self) -> None:
        state = self.state("write")
        facts = dict(
            connection_id=state.connection_id,
            config_revision=1,
            policy_revision=1,
            verified=True,
            export_allowed=True,
        )
        self.assertTrue(state.accepts_access(**facts))
        for changes in (
            {"config_revision": 2},
            {"policy_revision": 2},
            {"export_allowed": False},
            {"verified": False},
            {"connection_id": identifier()},
        ):
            self.assertFalse(state.accepts_access(**(facts | changes)))
        read = self.state("read")
        self.assertTrue(
            read.accepts_access(
                connection_id=read.connection_id,
                config_revision=1,
                policy_revision=99,
                verified=True,
                export_allowed=False,
            )
        )

    def test_catalog_event_selects_only_changed_variant_and_inherited_siblings(
        self,
    ) -> None:
        from test.catalog_support import default_schema
        from src.modules.catalog.domain.catalog_item.entity.variant import (
            CatalogVariant,
        )

        schema = default_schema()
        now = datetime.now(UTC)
        actor = identifier()
        root = CatalogItem.create_variable(
            identifier=CatalogItemIdVO(uuid4()),
            actor=actor,
            now=now,
            product_type_id=schema.id,
        )
        children = [
            CatalogVariant.create(
                identifier=CatalogItemIdVO(uuid4()),
                parent_id=root.id,
                actor=actor,
                now=now,
            )
            for _ in range(2)
        ]
        for child in children:
            root.add_variant(variant=child, actor=actor, now=now, schema=schema)
        root.update(
            fields=frozenset({"stock"}),
            actor=actor,
            now=now,
            stock=StockSpecificationVO(True, 10, None, BackorderPolicy.NO),
        )
        self.assertEqual(
            set(root.pull_stock_events()[0].position_ids),
            {root.id, *[v.id for v in children]},
        )
        own = children[0].changed(
            fields=frozenset({"stock"}),
            actor=actor,
            now=now,
            stock=StockSpecificationVO(True, 3, None, BackorderPolicy.NO),
        )
        root.change_variant(variant=own, actor=actor, now=now)
        self.assertEqual(root.pull_stock_events()[0].position_ids, (own.id,))
        root.update(
            fields=frozenset({"stock"}),
            actor=actor,
            now=now,
            stock=StockSpecificationVO(True, 11, None, BackorderPolicy.NO),
        )
        self.assertEqual(
            set(root.pull_stock_events()[0].position_ids), {root.id, children[1].id}
        )

    def test_duplicate_native_marketplace_target_blocks_distinct_publications(
        self,
    ) -> None:
        first = StockLinkFacts(
            identifier(),
            identifier(),
            identifier(),
            identifier(),
            3,
            "no",
            "rozetka.item:42",
        )
        second = replace(
            first, publication_id=identifier(), platform_owner_id=identifier()
        )
        with self.assertRaisesRegex(StockSyncError, "stock_ownership_ambiguous"):
            StockOwnershipPolicy().ensure_exportable(first, (first, second))


class StockPlatformTests(unittest.IsolatedAsyncioTestCase):
    def platform(self, kind: str, responses: list) -> tuple:
        http = FixtureHttp(responses)
        platform = InstalledPlatforms(http).get(kind)
        config = ConnectionConfigVO.create(
            version=1,
            endpoint=(
                "https://shop.example"
                if kind == "woocommerce"
                else (
                    "https://my.prom.ua"
                    if kind == "prom"
                    else "https://api-seller.rozetka.com.ua"
                )
            ),
            settings={},
        )
        return (
            platform,
            http,
            config,
            (
                b'{"consumer_key":"ck_real","consumer_secret":"cs_real"}'
                if kind == "woocommerce"
                else b'{"token":"real_token"}'
            ),
        )

    async def test_prom_absolute_array_write_and_readback(self) -> None:
        before = {
            "product": {"id": 101, "quantity_in_stock": 2, "presence": "available"}
        }
        after = {
            "product": {"id": 101, "quantity_in_stock": 0, "presence": "not_available"}
        }
        p, http, config, secret = self.platform(
            "prom", [before, {"processed_ids": [101], "errors": {}}, after]
        )
        result = await p.set_stock(
            config=config,
            credentials=secret,
            publication=lookup(),
            quantity=0,
            backorders="no",
        )
        self.assertEqual(result.stock.quantity, 0)
        self.assertEqual(http.calls[1][0], "POST")
        self.assertEqual(
            http.calls[1][2]["body"],
            [
                {
                    "id": 101,
                    "quantity_in_stock": 0,
                    "presence": "not_available",
                    "in_stock": False,
                }
            ],
        )
        self.assertEqual(
            http.calls[1][2]["headers"]["Authorization"], "Bearer real_token"
        )

    async def test_prom_per_item_failure_is_not_success(self) -> None:
        p, http, config, secret = self.platform(
            "prom",
            [
                {
                    "product": {
                        "id": 101,
                        "quantity_in_stock": 5,
                        "presence": "available",
                    }
                },
                {"processed_ids": [], "errors": {"101": "private provider text"}},
            ],
        )
        with self.assertRaisesRegex(
            VerificationFailure, "stock_write_rejected"
        ) as error:
            await p.set_stock(
                config=config,
                credentials=secret,
                publication=lookup(),
                quantity=5,
                backorders="no",
            )
        self.assertNotIn("private", str(error.exception))
        self.assertEqual([call[0] for call in http.calls], ["GET", "POST"])

    async def test_prom_empty_ack_is_confirmed_by_actual_quantity_and_presence(
        self,
    ) -> None:
        response = json.loads(
            (
                Path(__file__).parent
                / "fixtures/channels/prom-stock-update-unchanged.json"
            ).read_text()
        )
        for before_quantity, quantity, presence, backorders, variant in (
            (7, 7, "available", "no", True),
            (2, 7, "available", "no", False),
            (5, 0, "not_available", "no", False),
            (0, 0, "order", "yes", True),
        ):
            with self.subTest(quantity=quantity, presence=presence, variant=variant):
                before = {
                    "product": {
                        "id": 101,
                        "quantity_in_stock": before_quantity,
                        "presence": "available",
                        "is_variation": variant,
                    }
                }
                after = {
                    "product": {
                        "id": 101,
                        "quantity_in_stock": quantity,
                        "presence": presence,
                        "is_variation": variant,
                    }
                }
                platform, http, config, secret = self.platform(
                    "prom", [before, response, after]
                )
                result = await platform.set_stock(
                    config=config,
                    credentials=secret,
                    publication=lookup(parent=variant),
                    quantity=quantity,
                    backorders=backorders,
                )
                self.assertEqual(result.stock.quantity, quantity)
                self.assertEqual(result.platform_data["presence"], presence)
                self.assertEqual(
                    [call[0] for call in http.calls], ["GET", "POST", "GET"]
                )

    async def test_prom_unconfirmed_state_retries_with_empty_or_processed_ids(
        self,
    ) -> None:
        for processed in ([], [101]):
            for value in (
                {"quantity_in_stock": 6, "presence": "available"},
                {"quantity_in_stock": 7, "presence": "not_available"},
                {
                    "quantity_in_stock": None,
                    "presence": "available",
                    "is_variation": True,
                },
            ):
                with self.subTest(processed=processed, value=value):
                    platform, http, config, secret = self.platform(
                        "prom",
                        [
                            {
                                "product": {
                                    "id": 101,
                                    "quantity_in_stock": 7,
                                    "presence": "available",
                                }
                            },
                            {"processed_ids": processed, "errors": {}},
                            {"product": {"id": 101, **value}},
                        ],
                    )
                    with (
                        self.assertLogs(
                            "src.modules.channels.infrastructure.platforms.prom.stock",
                            level="WARNING",
                        ),
                        self.assertRaises(VerificationFailure) as error,
                    ):
                        await platform.set_stock(
                            config=config,
                            credentials=secret,
                            publication=lookup(),
                            quantity=7,
                            backorders="no",
                        )
                    self.assertEqual(error.exception.code, "stock_write_unconfirmed")
                    self.assertTrue(error.exception.retryable)
                    self.assertEqual(len(http.calls), 3)

    async def test_prom_warning_is_logged_safely_and_does_not_override_readback(
        self,
    ) -> None:
        product = {
            "product": {"id": 101, "quantity_in_stock": 7, "presence": "available"}
        }
        platform, http, config, secret = self.platform(
            "prom",
            [
                product,
                {
                    "processed_ids": [],
                    "errors": {},
                    "warnings": {"101": "private provider text real_token"},
                },
                product,
            ],
        )
        publication = lookup()
        with self.assertLogs(
            "src.modules.channels.infrastructure.platforms.prom.stock", level="WARNING"
        ) as logs:
            result = await platform.set_stock(
                config=config,
                credentials=secret,
                publication=publication,
                quantity=7,
                backorders="no",
            )
        self.assertEqual(result.stock.quantity, 7)
        record = logs.records[0]
        self.assertEqual(record.publication_id, str(publication.id))
        self.assertEqual(record.external_id, "101")
        self.assertEqual(
            (record.processed_count, record.error_count, record.warning_count),
            (0, 0, 1),
        )
        self.assertFalse(record.target_processed)
        self.assertNotIn("private", str(logs.output))
        self.assertNotIn("real_token", str(logs.output))

    async def test_prom_error_code_logs_do_not_include_tokens_or_provider_text(
        self,
    ) -> None:
        for code, expected_code in (
            ("stock_read_only", "stock_read_only"),
            ("real_token", None),
            (403, 403),
        ):
            with self.subTest(code=code):
                platform, http, config, secret = self.platform(
                    "prom",
                    [
                        {
                            "product": {
                                "id": 101,
                                "quantity_in_stock": 7,
                                "presence": "available",
                            }
                        },
                        {
                            "processed_ids": [],
                            "errors": {
                                "101": {
                                    "code": code,
                                    "message": "private provider text real_token",
                                }
                            },
                        },
                    ],
                )
                with (
                    self.assertLogs(
                        "src.modules.channels.infrastructure.platforms.prom.stock",
                        level="WARNING",
                    ) as logs,
                    self.assertRaisesRegex(VerificationFailure, "stock_write_rejected"),
                ):
                    await platform.set_stock(
                        config=config,
                        credentials=secret,
                        publication=lookup(),
                        quantity=7,
                        backorders="no",
                    )
                self.assertEqual(
                    getattr(logs.records[0], "provider_error_code", None), expected_code
                )
                self.assertNotIn("private", str(logs.output))
                self.assertNotIn("real_token", str(logs.output))
                self.assertEqual(len(http.calls), 2)

    async def test_prom_invalid_ack_and_readback_identity_cannot_complete(self) -> None:
        for response in ({"processed_ids": ["101"], "errors": {}}, {"errors": {}}):
            with self.subTest(response=response):
                platform, http, config, secret = self.platform(
                    "prom",
                    [
                        {
                            "product": {
                                "id": 101,
                                "quantity_in_stock": 7,
                                "presence": "available",
                            }
                        },
                        response,
                    ],
                )
                with self.assertRaises(ValidationError):
                    await platform.set_stock(
                        config=config,
                        credentials=secret,
                        publication=lookup(),
                        quantity=7,
                        backorders="no",
                    )
                self.assertEqual(len(http.calls), 2)
        platform, http, config, secret = self.platform(
            "prom",
            [
                {
                    "product": {
                        "id": 101,
                        "quantity_in_stock": 7,
                        "presence": "available",
                    }
                },
                {"processed_ids": [], "errors": {}},
                {
                    "product": {
                        "id": 102,
                        "quantity_in_stock": 7,
                        "presence": "available",
                    }
                },
            ],
        )
        with self.assertRaisesRegex(
            VerificationFailure, "publication_identity_invalid"
        ):
            await platform.set_stock(
                config=config,
                credentials=secret,
                publication=lookup(),
                quantity=7,
                backorders="no",
            )

    async def test_prom_unknown_inheritance_is_blocked_before_write(self) -> None:
        p, http, config, secret = self.platform(
            "prom",
            [
                {
                    "product": {
                        "id": 101,
                        "quantity_in_stock": None,
                        "is_variation": True,
                        "variation_base_id": 100,
                    }
                }
            ],
        )
        with self.assertRaisesRegex(VerificationFailure, "stock_ownership_ambiguous"):
            await p.set_stock(
                config=config,
                credentials=secret,
                publication=lookup(parent=True),
                quantity=5,
                backorders="no",
            )
        self.assertEqual(len(http.calls), 1)

    async def test_woo_independent_variation_write_only_stock_fields(self) -> None:
        after = {
            "id": 101,
            "manage_stock": True,
            "stock_quantity": 4,
            "stock_status": "instock",
            "backorders": "notify",
        }
        p, http, config, secret = self.platform("woocommerce", [after, after])
        result = await p.set_stock(
            config=config,
            credentials=secret,
            publication=lookup(
                "variation", parent=True, native={"parent_product_id": "100"}
            ),
            quantity=4,
            backorders="notify",
        )
        self.assertEqual(result.stock.quantity, 4)
        self.assertTrue(http.calls[0][1].endswith("/products/100/variations/101"))
        self.assertEqual(
            http.calls[0][2]["body"],
            {"manage_stock": True, "stock_quantity": 4, "backorders": "notify"},
        )

    async def test_woo_inherited_and_legacy_false_resolve_actual_parent(self) -> None:
        for mode in ("parent", False):
            p, http, config, secret = self.platform(
                "woocommerce",
                [
                    {"id": 101, "manage_stock": mode, "stock_quantity": None},
                    {"id": 100, "manage_stock": True, "stock_quantity": 15},
                ],
            )
            parent = lookup(external="100")
            child = lookup(
                "variation", parent=True, native={"parent_product_id": "100"}
            )
            result = await p.get_stock(
                config=config, credentials=secret, publication=child, parent=parent
            )
            self.assertEqual(result.stock.external_id, "100")
            self.assertEqual(result.stock.quantity, 15)

    async def test_woo_null_quantity_is_not_zero(self) -> None:
        p, http, config, secret = self.platform(
            "woocommerce", [{"id": 101, "manage_stock": True, "stock_quantity": None}]
        )
        self.assertIsNone(
            (
                await p.get_stock(
                    config=config, credentials=secret, publication=lookup()
                )
            ).stock.quantity
        )

    def rozetka_item(
        self,
        quantity: int | None,
        *,
        availability: int = 4,
        rz_id: int | None = 42,
        source_availability: int = 1,
    ) -> dict:
        return {
            "success": True,
            "content": {
                "item": {
                    "sync_source_id": 7,
                    "price_offer_id": "offer-1",
                    "item_id": 9,
                    "rz_item_id": rz_id,
                    "stock_quantity": quantity,
                    "available": source_availability,
                    "sync_source": {"availability": availability},
                }
            },
        }

    def rozetka_lookup(self) -> PublicationLookup:
        return lookup(
            "source_offer",
            "7:offer-1",
            native={"item_id": 9, "rz_item_id": 42, "sync_source_id": 7},
        )

    async def test_rozetka_token_and_confirmed_write_id_without_prices(self) -> None:
        p, http, config, secret = self.platform(
            "rozetka",
            [
                self.rozetka_item(3),
                {"success": True, "content": None},
                self.rozetka_item(0, source_availability=0),
            ],
        )
        result = await p.set_stock(
            config=config,
            credentials=secret,
            publication=self.rozetka_lookup(),
            quantity=0,
            backorders="no",
        )
        self.assertEqual(result.stock.quantity, 0)
        self.assertEqual(http.calls[1][0], "PUT")
        self.assertEqual(
            http.calls[1][2]["body"],
            {"items": [{"item_rz_id": 42, "stock_quantity": 0}]},
        )
        self.assertEqual(
            http.calls[0][2]["headers"]["Authorization"], "Bearer real_token"
        )

    async def test_rozetka_price_feed_mode_and_missing_marketplace_id_block_writes(
        self,
    ) -> None:
        for native, code in [
            (self.rozetka_item(3, availability=3), "stock_source_api_required"),
            (self.rozetka_item(3, rz_id=None), "stock_write_identity_unavailable"),
        ]:
            p, http, config, secret = self.platform("rozetka", [native])
            with self.assertRaisesRegex(VerificationFailure, code):
                await p.set_stock(
                    config=config,
                    credentials=secret,
                    publication=self.rozetka_lookup(),
                    quantity=5,
                    backorders="no",
                )
            self.assertEqual(len(http.calls), 1)

    async def test_rozetka_removed_is_not_zero(self) -> None:
        p, http, config, secret = self.platform(
            "rozetka", [self.rozetka_item(None, source_availability=2)]
        )
        result = await p.get_stock(
            config=config, credentials=secret, publication=self.rozetka_lookup()
        )
        self.assertIsNone(result.stock.quantity)
        self.assertEqual(result.stock.availability, "removed")

    async def test_rozetka_partial_error_is_safe_failure(self) -> None:
        p, http, config, secret = self.platform(
            "rozetka",
            [
                self.rozetka_item(3),
                {"success": False, "errors": {"42": {"reason": "private message"}}},
            ],
        )
        with self.assertRaisesRegex(VerificationFailure, "stock_write_rejected"):
            await p.set_stock(
                config=config,
                credentials=secret,
                publication=self.rozetka_lookup(),
                quantity=5,
                backorders="no",
            )

    async def test_read_identity_mismatch_is_rejected_for_each_platform(self) -> None:
        for kind, response, pub in [
            ("prom", {"product": {"id": 102}}, lookup()),
            ("woocommerce", {"id": 102, "manage_stock": True}, lookup()),
            (
                "rozetka",
                self.rozetka_item(3),
                lookup("source_offer", "7:other", native={"item_id": 9}),
            ),
        ]:
            p, http, config, secret = self.platform(kind, [response])
            with (
                self.subTest(kind=kind),
                self.assertRaisesRegex(
                    VerificationFailure, "publication_identity_invalid"
                ),
            ):
                await p.get_stock(config=config, credentials=secret, publication=pub)
