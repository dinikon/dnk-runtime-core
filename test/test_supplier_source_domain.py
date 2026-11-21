from src.modules.supplier_sourcing.domain.value_object.supplier_reference import (
    SupplierReferenceVO,
)

"""Карточка источника поставщика, режимы, сроки и настройки наличия."""

import unittest
from dataclasses import FrozenInstanceError, replace
from datetime import timedelta
from uuid import uuid4

from src.modules.shared.domain.domain_error import EntityIdTypeError
from src.modules.supplier_sourcing.domain.error import InvalidSupplierLeadTimeError
from src.modules.supplier_sourcing.domain.supplier_source.aggregate import (
    SupplierSource,
)
from src.modules.supplier_sourcing.domain.supplier_source.error import (
    InvalidSupplierSourceValueError,
    InvalidSupplierStockUpdatePolicyError,
    SupplierSourceInactiveError,
    UnsupportedSupplierFulfillmentModeError,
)
from src.modules.supplier_sourcing.domain.supplier_source.value_object.external_warehouse_code import (
    ExternalWarehouseCodeVO,
)
from src.modules.supplier_sourcing.domain.supplier_source.value_object.fulfillment_mode import (
    SupplierFulfillmentMode,
)
from src.modules.supplier_sourcing.domain.supplier_source.value_object.identifier import (
    SupplierSourceIdVO,
)
from src.modules.supplier_sourcing.domain.supplier_source.value_object.name import (
    SupplierSourceNameVO,
)
from src.modules.supplier_sourcing.domain.supplier_source.value_object.stock_update_policy import (
    MissingSkuBehavior,
    StaleStockBehavior,
    SupplierStockUpdatePolicyVO,
)
from src.modules.supplier_sourcing.domain.value_object.lead_time import (
    SupplierLeadTimeVO,
)
from src.modules.supplier_sourcing.domain.value_object.supplier_id import SupplierIdVO


class SupplierSourceValueObjectTests(unittest.TestCase):
    """Проверяет значения карточки отдельно от жизненного цикла источника."""

    def test_identifiers_are_nominal_uuid_values(self) -> None:
        """Один UUID в двух контрактах имеет разные доменные значения."""
        identifier = uuid4()
        self.assertNotEqual(SupplierSourceIdVO(identifier), SupplierIdVO(identifier))
        for identifier_type in (SupplierSourceIdVO, SupplierIdVO):
            with self.subTest(identifier_type=identifier_type):
                with self.assertRaises(EntityIdTypeError):
                    identifier_type(str(identifier))

    def test_display_name_and_external_code_preserve_case(self) -> None:
        """Пробелы по краям удаляются, код поставщика сохраняет регистр и нули."""
        self.assertEqual(SupplierSourceNameVO("  Склад Киев  ").value, "Склад Киев")
        self.assertEqual(ExternalWarehouseCodeVO("  001-Kyiv  ").value, "001-Kyiv")
        self.assertNotEqual(
            ExternalWarehouseCodeVO("001-Kyiv"), ExternalWarehouseCodeVO("001-kyiv")
        )

    def test_text_values_reject_empty_invalid_and_control_characters(self) -> None:
        """Имя и заданный код требуют отображаемого непустого текста."""
        for factory in (SupplierSourceNameVO, ExternalWarehouseCodeVO):
            for value in (None, True, 123, "", "  ", "Kyiv\n", "Ky\u200biv"):
                with (
                    self.subTest(factory=factory, value=value),
                    self.assertRaises(InvalidSupplierSourceValueError),
                ):
                    factory(value)

    def test_lead_time_and_ttl_have_distinct_zero_rules(self) -> None:
        """Немедленная поставка допустима, а интервал актуальности должен быть положительным."""
        self.assertEqual(SupplierLeadTimeVO(timedelta(0)).value, timedelta(0))
        for value in (None, True, 2, timedelta(microseconds=-1)):
            with (
                self.subTest(value=value),
                self.assertRaises(InvalidSupplierLeadTimeError),
            ):
                SupplierLeadTimeVO(value)
        for value in (None, True, 2, timedelta(0), timedelta(seconds=-1)):
            with (
                self.subTest(value=value),
                self.assertRaises(InvalidSupplierStockUpdatePolicyError),
            ):
                SupplierStockUpdatePolicyVO(
                    value, StaleStockBehavior.MARK_UNKNOWN, MissingSkuBehavior.KEEP_LAST
                )

    def test_stock_policy_requires_distinct_typed_behaviors(self) -> None:
        """Совпадение строковых значений не делает два вида настроек взаимозаменяемыми."""
        for stale, missing in (
            ("MARK_UNKNOWN", MissingSkuBehavior.KEEP_LAST),
            (MissingSkuBehavior.MARK_UNKNOWN, MissingSkuBehavior.KEEP_LAST),
            (StaleStockBehavior.MARK_UNKNOWN, "KEEP_LAST"),
            (StaleStockBehavior.BLOCK_AUTOMATIC_SALE, StaleStockBehavior.MARK_UNKNOWN),
        ):
            with (
                self.subTest(stale=stale, missing=missing),
                self.assertRaises(InvalidSupplierStockUpdatePolicyError),
            ):
                SupplierStockUpdatePolicyVO(timedelta(hours=1), stale, missing)


class SupplierSourceDomainTests(unittest.TestCase):
    """Проверяет фабрики, изменение настроек и пригодность источника."""

    def setUp(self) -> None:
        """Готовит активный источник прямой поставки одного поставщика."""
        self.identifier = SupplierSourceIdVO(uuid4())
        self.supplier = SupplierReferenceVO.from_value("crm.company", uuid4())
        self.policy = SupplierStockUpdatePolicyVO(
            ttl=timedelta(hours=2),
            stale_behavior=StaleStockBehavior.MARK_UNKNOWN,
            missing_sku_behavior=MissingSkuBehavior.KEEP_LAST,
        )
        self.source = self.create()

    def create(self, **changes: object) -> SupplierSource:
        """Создаёт источник с явными настройками и возможностью заменить входы в тесте."""
        return SupplierSource.create(
            **(
                dict(
                    identifier=self.identifier,
                    supplier=self.supplier,
                    name=SupplierSourceNameVO("Киев"),
                    fulfillment_modes=frozenset({SupplierFulfillmentMode.DROPSHIP}),
                    stock_update_policy=self.policy,
                    default_lead_time=SupplierLeadTimeVO(timedelta(days=1)),
                )
                | changes
            )
        )

    def test_one_supplier_can_have_two_sources_with_different_modes_and_lead_times(
        self,
    ) -> None:
        """Один контрагент может отправлять напрямую из одного источника и на наш склад из другого."""
        second = self.create(
            identifier=SupplierSourceIdVO(uuid4()),
            name=SupplierSourceNameVO("Львов"),
            external_warehouse_code=ExternalWarehouseCodeVO("Lviv-02"),
            fulfillment_modes=frozenset(
                {SupplierFulfillmentMode.PURCHASE_TO_WAREHOUSE}
            ),
            default_lead_time=SupplierLeadTimeVO(timedelta(days=3)),
        )
        self.assertEqual(self.source.supplier, second.supplier)
        self.assertNotEqual(self.source.id, second.id)
        self.assertNotEqual(self.source.default_lead_time, second.default_lead_time)
        self.assertTrue(self.source.is_active)
        self.assertTrue(second.is_active)
        self.assertIsNone(self.source.external_warehouse_code)
        self.source.ensure_supports(SupplierFulfillmentMode.DROPSHIP)
        second.ensure_supports(SupplierFulfillmentMode.PURCHASE_TO_WAREHOUSE)
        with self.assertRaises(UnsupportedSupplierFulfillmentModeError):
            second.ensure_supports(SupplierFulfillmentMode.DROPSHIP)

    def test_restore_preserves_all_fields_and_inactive_state(self) -> None:
        """Восстановление сохраняет внешний код, принадлежность, настройки и блокировку."""
        source = self.source.change_external_warehouse_code(
            ExternalWarehouseCodeVO("Kyiv-01")
        ).deactivate()
        arguments = dict(
            identifier=source.id,
            supplier=source.supplier,
            name=source.name,
            external_warehouse_code=source.external_warehouse_code,
            fulfillment_modes=source.fulfillment_modes,
            is_active=source.is_active,
            stock_update_policy=source.stock_update_policy,
            default_lead_time=source.default_lead_time,
        )
        restored = SupplierSource.restore(**arguments)
        self.assertEqual(restored, source)
        with self.assertRaises(SupplierSourceInactiveError):
            restored.ensure_supports(SupplierFulfillmentMode.DROPSHIP)
        for value in (0, 1, "false", None):
            with (
                self.subTest(value=value),
                self.assertRaises(InvalidSupplierSourceValueError),
            ):
                SupplierSource.restore(**(arguments | dict(is_active=value)))

    def test_invalid_identifiers_values_and_mode_collections_are_rejected(self) -> None:
        """Одинаковый UUID другого назначения и сырые настройки не проходят границу корня."""
        for changes in (
            dict(identifier=self.supplier),
            dict(supplier=self.identifier),
            dict(supplier=self.supplier.identifier.uuid),
            dict(name="Киев"),
            dict(external_warehouse_code="Kyiv-01"),
            dict(stock_update_policy=timedelta(hours=2)),
            dict(default_lead_time=timedelta(days=1)),
            dict(fulfillment_modes=frozenset()),
            dict(fulfillment_modes={SupplierFulfillmentMode.DROPSHIP}),
            dict(fulfillment_modes=frozenset({"DROPSHIP"})),
            dict(fulfillment_modes=frozenset({None, SupplierFulfillmentMode.DROPSHIP})),
        ):
            with (
                self.subTest(changes=changes),
                self.assertRaises(InvalidSupplierSourceValueError),
            ):
                self.create(**changes)
        with self.assertRaises(InvalidSupplierSourceValueError):
            self.source.ensure_supports("DROPSHIP")

    def test_configures_both_modes_and_updates_inactive_source_without_reassigning_it(
        self,
    ) -> None:
        """Настройки можно исправить до активации, сохраняя ID и прежний экземпляр."""
        policy = SupplierStockUpdatePolicyVO(
            timedelta(minutes=30),
            StaleStockBehavior.BLOCK_AUTOMATIC_SALE,
            MissingSkuBehavior.MARK_UNKNOWN,
        )
        inactive = self.source.deactivate()
        updated = (
            inactive.rename(SupplierSourceNameVO("Киев Центр"))
            .change_external_warehouse_code(ExternalWarehouseCodeVO("Kyiv-02"))
            .change_stock_update_policy(policy)
            .configure_fulfillment(
                fulfillment_modes=frozenset(SupplierFulfillmentMode),
                default_lead_time=SupplierLeadTimeVO(timedelta(0)),
            )
        )
        self.assertEqual(updated.id, self.source.id)
        self.assertEqual(updated.supplier, self.source.supplier)
        self.assertEqual(updated.name.value, "Киев Центр")
        self.assertEqual(updated.stock_update_policy, policy)
        self.assertEqual(updated.default_lead_time.value, timedelta(0))
        self.assertEqual(updated.external_warehouse_code.value, "Kyiv-02")
        self.assertIsNone(
            updated.change_external_warehouse_code(None).external_warehouse_code
        )
        self.assertEqual(inactive.name.value, "Киев")
        self.assertEqual(inactive.stock_update_policy, self.policy)
        self.assertFalse(updated.is_active)
        for mode in SupplierFulfillmentMode:
            with self.assertRaises(SupplierSourceInactiveError):
                updated.ensure_supports(mode)
            updated.activate().ensure_supports(mode)

    def test_activity_transitions_are_idempotent_and_failed_update_keeps_state(
        self,
    ) -> None:
        """Повторный переход не меняет смысл карточки, а отказ сохраняет исходное состояние."""
        inactive = self.source.deactivate()
        self.assertEqual(inactive, inactive.deactivate())
        self.assertEqual(self.source, self.source.activate())
        self.assertEqual(inactive.activate(), self.source)
        with self.assertRaises(InvalidSupplierSourceValueError):
            inactive.configure_fulfillment(
                fulfillment_modes=frozenset(),
                default_lead_time=inactive.default_lead_time,
            )
        self.assertEqual(inactive, replace(self.source, is_active=False))
        with self.assertRaises(FrozenInstanceError):
            self.source.supplier = SupplierReferenceVO.from_value(
                "crm.company", uuid4()
            )
