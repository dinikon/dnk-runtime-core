"""Инварианты представления, семантика overrides и подготовка итогового контента."""

from datetime import datetime, UTC, timedelta
import unittest
from uuid import uuid4

from src.modules.channels.domain.product_representation.aggregate import (
    ProductRepresentation,
)
from src.modules.channels.domain.product_representation.error import (
    ProductRepresentationError,
)
from src.modules.channels.domain.product_representation.overrides import (
    RepresentationOverridesVO,
    LocalizedOverridesVO,
    ItemOverridesVO,
)
from src.modules.channels.domain.product_representation.policy import (
    RepresentationPolicy,
)
from src.modules.channels.domain.catalog_binding.value_object import BindingMode
from src.modules.channels.domain.product_representation.value_object import (
    ContentImage,
    ContentOrigin,
)
from src.modules.channels.infrastructure.product_representation.document import (
    encode_overrides,
    decode_overrides,
    OVERRIDES_SCHEMA,
)
from src.modules.channels.application.error import ChannelInputError
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from test import test_channels_representation as support


class RepresentationOverridesDomainTests(unittest.TestCase):
    """Проверяет отдельные переходы без SQL и внешних API."""

    def setUp(self) -> None:
        """Создаёт новое представление с первой ревизией и запретом экспорта."""
        self.now = datetime.now(UTC)
        self.actor = EntityIdVO(uuid4())
        self.item = EntityIdVO(uuid4())
        self.root = ProductRepresentation.create(
            identifier=EntityIdVO(uuid4()),
            binding_group_id=EntityIdVO(uuid4()),
            overrides=RepresentationOverridesVO(),
            actor=self.actor,
            now=self.now,
        )

    def test_revision_noop_enable_disable_and_invalid_operation_atomicity(self) -> None:
        """Разрешение, контент и аудит меняются только после успешных проверок."""
        self.assertEqual((self.root.revision, self.root.export_enabled), (1, False))
        self.root.change_overrides(
            overrides=RepresentationOverridesVO(),
            expected_revision=1,
            export_ready=True,
            actor=self.actor,
            now=self.now + timedelta(seconds=1),
        )
        self.assertEqual((self.root.revision, self.root.updated_at), (1, self.now))
        with self.assertRaises(ProductRepresentationError):
            self.root.enable_export(
                expected_revision=1,
                blockers=("representation_title_missing",),
                actor=self.actor,
                now=self.now,
            )
        self.assertEqual((self.root.revision, self.root.export_enabled), (1, False))
        self.root.enable_export(
            expected_revision=1, blockers=(), actor=self.actor, now=self.now
        )
        self.root.enable_export(
            expected_revision=2, blockers=(), actor=self.actor, now=self.now
        )
        self.assertEqual((self.root.revision, self.root.export_enabled), (2, True))
        changed = RepresentationOverridesVO(
            common=(LocalizedOverridesVO("uk", title="New"),)
        )
        with self.assertRaises(ProductRepresentationError):
            self.root.change_overrides(
                overrides=changed,
                expected_revision=1,
                export_ready=True,
                actor=self.actor,
                now=self.now,
            )
        self.assertEqual(self.root.overrides, RepresentationOverridesVO())
        self.root.change_overrides(
            overrides=changed,
            expected_revision=2,
            export_ready=False,
            actor=self.actor,
            now=self.now,
        )
        self.assertEqual((self.root.revision, self.root.export_enabled), (3, False))
        self.root.disable_export(expected_revision=3, actor=self.actor, now=self.now)
        self.assertEqual(self.root.revision, 3)
        with self.assertRaises(ProductRepresentationError):
            self.root.change_overrides(
                overrides=RepresentationOverridesVO(),
                expected_revision=3,
                export_ready=True,
                actor=self.actor,
                now=self.now - timedelta(days=1),
            )
        self.assertEqual((self.root.revision, self.root.overrides), (3, changed))

    def test_reconcile_preserves_only_unchanged_pairs_and_invalidates_permission(
        self,
    ) -> None:
        """Даже при пустых overrides изменение состава инвалидирует открытый редактор."""
        removed = EntityIdVO(uuid4())
        values = RepresentationOverridesVO(
            common=(LocalizedOverridesVO("uk", title="Common"),),
            items=(
                ItemOverridesVO(self.item, (LocalizedOverridesVO("uk", body="Keep"),)),
                ItemOverridesVO(removed, (LocalizedOverridesVO("ru", body="Drop"),)),
            ),
        )
        self.root.change_overrides(
            overrides=values,
            expected_revision=1,
            export_ready=True,
            actor=self.actor,
            now=self.now,
        )
        self.root.enable_export(
            expected_revision=2, blockers=(), actor=self.actor, now=self.now
        )
        self.root.reconcile_binding_items(
            retained_ids=(self.item,), actor=self.actor, now=self.now
        )
        self.assertEqual((self.root.revision, self.root.export_enabled), (4, False))
        self.assertEqual(self.root.overrides.common, values.common)
        self.assertEqual(
            [item.binding_item_id for item in self.root.overrides.items], [self.item]
        )
        self.assertIsNone(
            self.root.overrides.item_for(
                binding_item_id=EntityIdVO(uuid4()), locale="uk"
            )
        )

    def test_values_are_immutable_canonical_and_distinguish_clear_from_reset(
        self,
    ) -> None:
        """Входные списки не меняют сохранённое намерение после создания VO."""
        images = [ContentImage(EntityIdVO(uuid4()), "Alt", "Caption")]
        localized = LocalizedOverridesVO("uk", body="", gallery=images)
        content = [localized, LocalizedOverridesVO("ru")]
        items = [ItemOverridesVO(self.item, content)]
        overrides = RepresentationOverridesVO(items=items)
        images.clear()
        content.clear()
        items.clear()
        self.assertEqual(len(overrides.items[0].content[0].gallery), 1)
        self.assertEqual(overrides.items[0].content[0].body, "")
        cleared = RepresentationOverridesVO(
            common=(LocalizedOverridesVO("uk", body="", gallery=()),)
        )
        self.assertEqual(
            encode_overrides(cleared),
            {"common": {"uk": {"body": "", "gallery": []}}, "items": {}},
        )
        self.assertEqual(
            decode_overrides(
                schema=OVERRIDES_SCHEMA, document=encode_overrides(cleared)
            ),
            cleared,
        )
        self.assertEqual(
            RepresentationOverridesVO(common=(LocalizedOverridesVO("uk"),)),
            RepresentationOverridesVO(),
        )
        for value in ("", "   "):
            with self.assertRaises(ProductRepresentationError):
                LocalizedOverridesVO("uk", title=value)
        with self.assertRaises(ChannelInputError):
            decode_overrides(schema="future.v2", document={})

    def test_composition_priority_sources_and_reset_to_common(self) -> None:
        """Общие значения и overrides пары применяются независимо для каждого поля."""
        setup = support.RepresentationPolicyTests()
        setup.setUp()
        pair = support.pair(setup.root, setup.pub)
        overrides = RepresentationOverridesVO(
            common=(LocalizedOverridesVO("uk", title="Group", body="Group body"),),
            items=(
                ItemOverridesVO(
                    pair.id, (LocalizedOverridesVO("uk", body="", gallery=()),)
                ),
            ),
        )
        prepared = setup.prepare(items=(pair,), overrides=overrides)
        value = prepared.targets[0].content[0]
        self.assertEqual((value.title, value.body, value.gallery), ("Group", "", ()))
        self.assertEqual(value.origins.title.kind, ContentOrigin.GROUP_OVERRIDE)
        self.assertEqual(value.origins.body.kind, ContentOrigin.ITEM_OVERRIDE)
        self.assertEqual(prepared.targets[0].catalog_content[0].title, "Назва")
        reset = setup.prepare(
            items=(pair,), overrides=RepresentationOverridesVO(common=overrides.common)
        )
        self.assertEqual(reset.targets[0].content[0].body, "Group body")
        other = setup.prepare(items=(pair,))
        self.assertEqual(other.targets[0].content[0].title, "Назва")

    def test_woo_common_applies_to_container_but_pair_override_only_to_variation(
        self,
    ) -> None:
        """Контейнер наследует общие поля без искусственной пары для его overrides."""
        setup = support.RepresentationPolicyTests()
        setup.setUp()
        pair = support.pair(setup.left, setup.child)
        prepared = setup.prepare(
            platform="woocommerce",
            mode=BindingMode.VARIABLE_TO_VARIABLE,
            catalog_root=support.content(setup.root, "variable"),
            catalog_positions=(support.content(setup.left, "variant"),),
            publications=(
                support.publication(setup.pub, "variable"),
                support.publication(setup.child, "variant", setup.pub),
            ),
            items=(pair,),
            overrides=RepresentationOverridesVO(
                common=(LocalizedOverridesVO("uk", title="Group"),),
                items=(
                    ItemOverridesVO(
                        pair.id, (LocalizedOverridesVO("uk", title="Item"),)
                    ),
                ),
            ),
        )
        container, variation = prepared.targets
        self.assertEqual(container.content[0].title, "Group")
        self.assertIsNone(container.binding_item_id)
        self.assertEqual(variation.content[0].title, "Item")
        self.assertEqual(variation.binding_item_id, pair.id)
        self.assertEqual([value.locale for value in variation.content], ["uk"])

    def test_scope_rejects_foreign_pairs_and_preserves_unchanged_inactive_language(
        self,
    ) -> None:
        """Смена конфигурации не уничтожает старый язык, но запрещает новые правки в нём."""
        previous = RepresentationOverridesVO(
            common=(LocalizedOverridesVO("ru", title="Old"),)
        )
        RepresentationPolicy.ensure_overrides_scope(
            overrides=previous,
            item_ids=(self.item,),
            locales=("uk",),
            previous=previous,
        )
        for candidate in (
            RepresentationOverridesVO(
                common=(LocalizedOverridesVO("ru", title="Changed"),)
            ),
            RepresentationOverridesVO(
                items=(
                    ItemOverridesVO(
                        EntityIdVO(uuid4()),
                        (LocalizedOverridesVO("uk", title="Foreign"),),
                    ),
                )
            ),
        ):
            with self.assertRaises(ProductRepresentationError):
                RepresentationPolicy.ensure_overrides_scope(
                    overrides=candidate,
                    item_ids=(self.item,),
                    locales=("uk",),
                    previous=previous,
                )

    def test_restore_rejects_bad_revision_audit_and_state(self) -> None:
        """Фабрика не исправляет повреждённые значения при восстановлении."""
        values = dict(
            identifier=self.root.id,
            binding_group_id=self.root.binding_group_id,
            revision=1,
            export_enabled=False,
            overrides=self.root.overrides,
            created_at=self.now,
            updated_at=self.now,
            created_by=self.actor,
            updated_by=self.actor,
        )
        for invalid in (
            {"revision": 0},
            {"revision": True},
            {"export_enabled": 1},
            {"overrides": {}},
            {"updated_at": self.now.replace(tzinfo=None)},
        ):
            with self.assertRaises(ProductRepresentationError):
                ProductRepresentation.restore(**(values | invalid))
