"""Чистая матрица структуры и атомарность агрегата привязок."""

import unittest
from datetime import datetime, UTC, timedelta
from uuid import uuid4
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.channels.domain.catalog_binding.aggregate import CatalogBindingGroup
from src.modules.channels.domain.catalog_binding.entity import CatalogBindingItem
from src.modules.channels.domain.catalog_binding.error import CatalogBindingError
from src.modules.channels.domain.catalog_binding.policy import BindingStructurePolicy
from src.modules.channels.domain.catalog_binding.value_object import (
    BindingMode,
    CatalogFamily,
    PublicationNode,
    BindingClaim,
)


def identifier():
    return EntityIdVO(uuid4())


def item(left, right):
    return CatalogBindingItem.create(
        identifier=identifier(), catalog_position_id=left, publication_id=right
    )


class BindingDomainTests(unittest.TestCase):
    def setUp(self):
        self.catalog, self.s, self.m = identifier(), identifier(), identifier()
        self.root, self.child, self.other = identifier(), identifier(), identifier()
        self.group, self.connection, self.actor = (
            identifier(),
            identifier(),
            identifier(),
        )
        self.now = datetime.now(UTC)
        self.policy = BindingStructurePolicy()

    def assess(
        self, mode, platform="prom", pairs=None, nodes=None, catalog=None, claims=()
    ):
        return self.policy.assess(
            mode=mode,
            catalog_root_id=self.catalog,
            catalog=catalog
            or CatalogFamily(
                self.catalog,
                "simple" if mode is BindingMode.SIMPLE_TO_SIMPLE else "variable",
                (
                    (self.catalog,)
                    if mode is BindingMode.SIMPLE_TO_SIMPLE
                    else (self.s, self.m)
                ),
            ),
            publication_root_id=(
                None if mode is BindingMode.VARIABLE_TO_SIMPLE else self.root
            ),
            items=tuple(pairs if pairs is not None else (item(self.s, self.root),)),
            nodes=tuple(
                nodes
                if nodes is not None
                else (
                    PublicationNode(self.root, "simple", None),
                    PublicationNode(self.child, "variant", self.root),
                )
            ),
            claims=claims,
            platform=platform,
            group_id=self.group,
        )

    def test_simple_and_variable_roles_are_explicit(self):
        simple = (PublicationNode(self.root, "simple", None),)
        for platform in ("prom", "woocommerce", "rozetka"):
            result = self.assess(
                BindingMode.SIMPLE_TO_SIMPLE,
                platform,
                pairs=(item(self.catalog, self.root),),
                nodes=simple,
            )
            self.assertEqual(result.state, "linked")
            variable = self.assess(
                BindingMode.VARIABLE_TO_SIMPLE, platform, nodes=simple
            )
            self.assertEqual(variable.state, "partial")
            forbidden = self.assess(
                BindingMode.SIMPLE_TO_SIMPLE,
                platform,
                pairs=(item(self.catalog, self.child),),
            )
            self.assertEqual(forbidden.state, "conflict")
        prom = self.assess(
            BindingMode.VARIABLE_TO_VARIABLE,
            pairs=(item(self.s, self.root), item(self.m, self.child)),
        )
        self.assertEqual(prom.state, "linked")
        woo = (
            PublicationNode(self.root, "variable", None),
            PublicationNode(self.child, "variant", self.root),
        )
        self.assertEqual(
            self.assess(
                BindingMode.VARIABLE_TO_VARIABLE,
                "woocommerce",
                pairs=(item(self.s, self.child),),
                nodes=woo,
            ).state,
            "partial",
        )
        self.assertIn(
            "binding_publication_position_invalid",
            self.assess(
                BindingMode.VARIABLE_TO_VARIABLE, "woocommerce", nodes=woo
            ).issues,
        )
        self.assertIn(
            "binding_variable_structure_invalid",
            self.assess(BindingMode.VARIABLE_TO_VARIABLE, "rozetka").issues,
        )

    def test_whole_family_reservation_even_unmapped_members(self):
        for claimed in (self.root, self.child):
            foreign = (BindingClaim(identifier(), claimed),)
            self.assertIn(
                "binding_publication_occupied",
                self.assess(BindingMode.VARIABLE_TO_VARIABLE, claims=foreign).issues,
            )
            own = (BindingClaim(self.group, claimed),)
            self.assertNotIn(
                "binding_publication_occupied",
                self.assess(BindingMode.VARIABLE_TO_VARIABLE, claims=own).issues,
            )
        changed = (
            PublicationNode(self.root, "simple", self.other),
            PublicationNode(self.other, "simple", None),
        )
        result = self.assess(
            BindingMode.VARIABLE_TO_SIMPLE,
            nodes=changed,
            claims=(BindingClaim(identifier(), self.other),),
        )
        self.assertIn("binding_publication_not_standalone", result.issues)
        self.assertIn("binding_publication_occupied", result.issues)

    def test_duplicate_pairs_and_wrong_catalog_are_conflicts(self):
        duplicate = (item(self.s, self.root), item(self.s, self.child))
        self.assertIn(
            "binding_position_duplicate",
            self.assess(BindingMode.VARIABLE_TO_VARIABLE, pairs=duplicate).issues,
        )
        self.assertIn(
            "binding_catalog_position_invalid",
            self.assess(
                BindingMode.VARIABLE_TO_VARIABLE, pairs=(item(identifier(), self.root),)
            ).issues,
        )
        self.assertIn(
            "binding_items_empty",
            self.assess(BindingMode.VARIABLE_TO_VARIABLE, pairs=()).issues,
        )

    def test_group_atomicity_noop_revision_and_restore_validation(self):
        pairs = (item(self.s, self.root),)
        group = CatalogBindingGroup.create(
            identifier=self.group,
            connection_id=self.connection,
            catalog_root_id=self.catalog,
            mode=BindingMode.VARIABLE_TO_VARIABLE,
            publication_root_id=self.root,
            items=pairs,
            actor=self.actor,
            now=self.now,
        )
        for bad in ((), (pairs[0], item(self.s, self.child))):
            with self.assertRaises(CatalogBindingError):
                group.change_items(
                    items=bad,
                    expected_revision=1,
                    actor=self.actor,
                    now=self.now + timedelta(seconds=1),
                )
            self.assertEqual(
                (group.revision, group.items, group.updated_at), (1, pairs, self.now)
            )
        group.change_items(
            items=(item(self.s, self.root),),
            expected_revision=1,
            actor=self.actor,
            now=self.now + timedelta(seconds=1),
        )
        self.assertEqual(group.revision, 1)
        self.assertEqual(group.items, pairs)
        group.change_items(
            items=(item(self.s, self.child),),
            expected_revision=1,
            actor=self.actor,
            now=self.now + timedelta(seconds=1),
        )
        self.assertEqual(group.revision, 2)
        with self.assertRaises(CatalogBindingError):
            group.require_revision(1)
        base = dict(
            identifier=self.group,
            connection_id=self.connection,
            catalog_root_id=self.catalog,
            mode=BindingMode.VARIABLE_TO_VARIABLE,
            publication_root_id=self.root,
            revision=1,
            items=pairs,
            created_at=self.now,
            updated_at=self.now,
            created_by=self.actor,
            updated_by=self.actor,
        )
        for invalid in (
            {"revision": 0},
            {"revision": True},
            {"mode": "VARIABLE_TO_VARIABLE"},
            {"publication_root_id": None},
            {"items": ()},
            {"updated_at": self.now - timedelta(seconds=1)},
            {"created_at": self.now.replace(tzinfo=None)},
        ):
            with self.assertRaises(CatalogBindingError):
                CatalogBindingGroup.restore(**(base | invalid))


class BindingWriteAtomicityTests(unittest.IsolatedAsyncioTestCase):
    async def test_rejected_external_structure_does_not_mutate_loaded_group(self):
        from types import SimpleNamespace
        from unittest.mock import AsyncMock, Mock
        from src.modules.channels.application.catalog_binding.writes import (
            BindingWrites,
        )
        from src.modules.channels.application.catalog_binding.contracts import (
            BindingPairDTO,
        )
        from src.modules.channels.domain.catalog_binding.value_object import (
            BindingAssessment,
        )

        now = datetime.now(UTC)
        left, right = identifier(), identifier()
        group = CatalogBindingGroup.create(
            identifier=identifier(),
            connection_id=identifier(),
            catalog_root_id=identifier(),
            mode=BindingMode.VARIABLE_TO_SIMPLE,
            publication_root_id=None,
            items=(item(left, right),),
            actor=identifier(),
            now=now,
        )
        initial = group.items
        catalog = SimpleNamespace(lock=AsyncMock())
        groups = SimpleNamespace(get=AsyncMock(return_value=group), save=AsyncMock())
        channel = SimpleNamespace(
            connection=SimpleNamespace(id=group.connection_id), platform_kind="prom"
        )
        channels = SimpleNamespace(get=AsyncMock(return_value=channel))
        views = SimpleNamespace(
            preview=AsyncMock(
                return_value=SimpleNamespace(
                    catalog_token="a" * 64,
                    publication_token="b" * 64,
                    assessment=BindingAssessment(
                        "conflict", ("binding_publication_not_standalone",), 1, 1, 1
                    ),
                )
            )
        )
        writes = BindingWrites(
            catalog,
            groups,
            channels,
            views,
            SimpleNamespace(new=Mock(side_effect=uuid4)),
            SimpleNamespace(get=AsyncMock(return_value=None), save=AsyncMock()),
        )
        with self.assertRaises(CatalogBindingError):
            await writes.update(
                tenant_id=uuid4(),
                channel_id=uuid4(),
                group_id=group.id.uuid,
                expected_revision=1,
                items=(BindingPairDTO(left.uuid, uuid4()),),
                catalog_token="a" * 64,
                publication_token="b" * 64,
                actor_id=group.created_by.uuid,
                now=now,
                locale="uk",
            )
        self.assertEqual(group.items, initial)
        self.assertEqual(group.revision, 1)
        groups.save.assert_not_awaited()
