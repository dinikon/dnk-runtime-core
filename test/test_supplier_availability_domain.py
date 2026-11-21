from src.modules.supplier_sourcing.domain.value_object.supplier_reference import (
    SupplierReferenceVO,
)

"""Наблюдения внешнего наличия, версии, хронология и актуальность по TTL."""

import unittest
from dataclasses import FrozenInstanceError, fields, replace
from datetime import UTC, datetime, timedelta, timezone
from decimal import Decimal
from itertools import product
from uuid import uuid4

from test import test_supplier_offer_domain as offer_fixture
from src.modules.supplier_sourcing.domain.supplier_availability.aggregate import (
    SupplierAvailability,
)
from src.modules.supplier_sourcing.domain.supplier_availability.error import (
    InvalidSupplierAvailabilityValueError,
    SupplierAvailabilityContextMismatchError,
    SupplierAvailabilityTimeError,
    SupplierAvailabilityVersionConflictError,
)
from src.modules.supplier_sourcing.domain.supplier_availability.value_object.identifier import (
    SupplierAvailabilityIdVO,
)
from src.modules.supplier_sourcing.domain.supplier_availability.value_object.observation import (
    AvailabilityStatus,
    AvailabilityType,
    SupplierAvailabilityObservationVO,
)
from src.modules.supplier_sourcing.domain.supplier_offer.value_object.uom_code import (
    SupplierOfferUomCodeVO,
)
from src.modules.supplier_sourcing.domain.supplier_source.value_object.stock_update_policy import (
    StaleStockBehavior,
)
from src.modules.supplier_sourcing.domain.value_object.supplier_id import SupplierIdVO


class SupplierAvailabilityObservationTests(unittest.TestCase):
    """Проверяет различие известного нуля, нижней границы и неизвестного количества."""

    def test_type_status_and_quantity_matrix(self) -> None:
        """Разрешены только согласованные сочетания данных наблюдения."""
        t, s = AvailabilityType, AvailabilityStatus
        zero, positive = Decimal(0), Decimal("15.250")
        valid = {
            (t.EXACT_QUANTITY, s.IN_STOCK, positive),
            (t.EXACT_QUANTITY, s.OUT_OF_STOCK, zero),
            (t.EXACT_QUANTITY, s.BACKORDER, zero),
            (t.LOWER_BOUND, s.IN_STOCK, positive),
            (t.LOWER_BOUND, s.UNKNOWN, zero),
            (t.STATUS_ONLY, s.IN_STOCK, None),
            (t.STATUS_ONLY, s.OUT_OF_STOCK, None),
            (t.STATUS_ONLY, s.BACKORDER, None),
            (t.UNKNOWN, s.UNKNOWN, None),
        }
        for kind, status, quantity in product(t, s, (None, zero, positive)):
            with self.subTest(kind=kind, status=status, quantity=quantity):
                if (kind, status, quantity) in valid:
                    observation = SupplierAvailabilityObservationVO(
                        kind, status, quantity
                    )
                    self.assertIs(observation.quantity, quantity)
                else:
                    with self.assertRaises(InvalidSupplierAvailabilityValueError):
                        SupplierAvailabilityObservationVO(kind, status, quantity)

    def test_invalid_types_and_nonfinite_quantities_are_rejected(self) -> None:
        """Числа без Decimal, нечисловые значения и сырые статусы отклоняются."""
        for value in (
            1,
            True,
            "1",
            Decimal("-1"),
            Decimal("sNaN"),
            Decimal("Infinity"),
        ):
            with (
                self.subTest(value=value),
                self.assertRaises(InvalidSupplierAvailabilityValueError),
            ):
                SupplierAvailabilityObservationVO(
                    AvailabilityType.EXACT_QUANTITY, AvailabilityStatus.IN_STOCK, value
                )
        for kind, status in (
            ("UNKNOWN", AvailabilityStatus.UNKNOWN),
            (AvailabilityType.UNKNOWN, "UNKNOWN"),
        ):
            with self.assertRaises(InvalidSupplierAvailabilityValueError):
                SupplierAvailabilityObservationVO(kind, status, None)


class SupplierAvailabilityDomainTests(unittest.TestCase):
    """Проверяет связь с предложением, приём наблюдений и оценку без чтения часов."""

    def setUp(self) -> None:
        """Готовит наблюдение 15 PCS для предложения, ограниченного источником."""
        self.f = offer_fixture.SupplierOfferDomainTests()
        self.f.setUp()
        self.source = self.f.source(self.f.supplier)
        self.offer = self.f.create(source=self.source.identity_snapshot())
        self.received_at = datetime(2026, 11, 7, 12, tzinfo=UTC)
        self.source_updated_at = self.received_at - timedelta(minutes=10)
        self.observation = SupplierAvailabilityObservationVO(
            AvailabilityType.EXACT_QUANTITY, AvailabilityStatus.IN_STOCK, Decimal(15)
        )
        self.availability = self.create()

    def create(self, **changes: object) -> SupplierAvailability:
        """Создаёт новое наблюдение через снимки настоящих агрегатов."""
        return SupplierAvailability.create(
            **(
                dict(
                    identifier=SupplierAvailabilityIdVO(uuid4()),
                    offer=self.offer.availability_snapshot(),
                    source=self.source.availability_snapshot(),
                    observation=self.observation,
                    uom=self.offer.base_uom,
                    received_at=self.received_at,
                    source_updated_at=self.source_updated_at,
                )
                | changes
            )
        )

    def record(self, **changes: object) -> SupplierAvailability:
        """Применяет наблюдение с актуальной версией и явно переопределяемыми датами."""
        return self.availability.record_observation(
            **(
                dict(
                    offer=self.offer.availability_snapshot(),
                    source=self.source.availability_snapshot(),
                    observation=self.observation,
                    uom=self.offer.base_uom,
                    received_at=self.received_at + timedelta(minutes=30),
                    expected_version=self.availability.version,
                    source_updated_at=self.source_updated_at,
                )
                | changes
            )
        )

    def restore(self, **changes: object) -> SupplierAvailability:
        """Восстанавливает полное сохранённое состояние без внешних агрегатов."""
        values = {
            field.name: getattr(self.availability, field.name)
            for field in fields(self.availability)
        }
        values["identifier"] = values.pop("id")
        return SupplierAvailability.restore(**(values | changes))

    def test_create_fixes_pair_and_ttl_from_received_time_in_utc(self) -> None:
        """TTL отсчитывается от получения, а время источника сохраняется отдельно."""
        zone = timezone(timedelta(hours=2))
        availability = self.create(
            received_at=self.received_at.astimezone(zone),
            source_updated_at=self.source_updated_at.astimezone(zone),
        )
        self.assertEqual(availability.supplier_offer_id, self.offer.id)
        self.assertEqual(availability.supplier_source_id, self.source.id)
        self.assertEqual(availability.base_uom, self.offer.base_uom)
        self.assertEqual(availability.version, 0)
        self.assertEqual(availability.received_at, self.received_at)
        self.assertEqual(availability.source_updated_at, self.source_updated_at)
        self.assertIs(availability.received_at.tzinfo, UTC)
        self.assertIs(availability.source_updated_at.tzinfo, UTC)
        self.assertEqual(availability.expires_at, self.received_at + timedelta(hours=2))

    def test_unrestricted_offer_accepts_own_source_but_bound_offer_requires_its_source(
        self,
    ) -> None:
        """Принадлежность поставщику проверяется для всех предложений, ограничение по ID — при его наличии."""
        alternate = self.f.source(self.f.supplier).availability_snapshot()
        foreign = self.f.source(
            SupplierReferenceVO.from_value("crm.company", uuid4())
        ).availability_snapshot()
        unrestricted = self.f.offer.availability_snapshot()
        self.assertEqual(
            self.create(offer=unrestricted, source=alternate).supplier_source_id,
            alternate.identity.id,
        )
        for changes in (
            dict(source=alternate),
            dict(source=foreign, offer=unrestricted),
            dict(uom=SupplierOfferUomCodeVO("KG")),
        ):
            with (
                self.subTest(changes=changes),
                self.assertRaises(SupplierAvailabilityContextMismatchError),
            ):
                self.create(**changes)
        for changes in (dict(offer=self.offer), dict(source=self.source)):
            with (
                self.subTest(changes=changes),
                self.assertRaises(InvalidSupplierAvailabilityValueError),
            ):
                self.create(**changes)

    def test_update_rejects_other_offer_source_or_changed_unit(self) -> None:
        """Подходящий сам по себе контекст не может переназначить существующее наблюдение."""
        alternate = self.f.source(self.f.supplier).availability_snapshot()
        offer = self.offer.availability_snapshot()
        different_unit = SupplierOfferUomCodeVO("KG")
        for changes in (
            dict(offer=self.f.offer.availability_snapshot()),
            dict(offer=replace(offer, source_id=None), source=alternate),
            dict(offer=replace(offer, base_uom=different_unit), uom=different_unit),
        ):
            with (
                self.subTest(changes=changes),
                self.assertRaises(SupplierAvailabilityContextMismatchError),
            ):
                self.record(**changes)

    def test_record_applies_new_observation_and_current_ttl(self) -> None:
        """Следующее наблюдение увеличивает версию и сохраняет ноль без изменения исходного экземпляра."""
        updated_source = self.source.change_stock_update_policy(
            replace(self.source.stock_update_policy, ttl=timedelta(hours=4))
        )
        zero = SupplierAvailabilityObservationVO(
            AvailabilityType.EXACT_QUANTITY, AvailabilityStatus.OUT_OF_STOCK, Decimal(0)
        )
        updated = self.record(
            observation=zero,
            source_updated_at=self.source_updated_at + timedelta(minutes=5),
            source=updated_source.availability_snapshot(),
        )
        self.assertEqual(updated.id, self.availability.id)
        self.assertEqual(updated.version, 1)
        self.assertEqual(updated.expires_at, updated.received_at + timedelta(hours=4))
        self.assertEqual(updated.observation, zero)
        self.assertEqual(self.availability.observation.quantity, Decimal(15))
        self.assertEqual(self.availability.version, 0)

    def test_version_and_exact_repeat_are_checked(self) -> None:
        """Точный повтор не продлевает TTL даже после смены политики, при этом версия должна совпадать."""
        source = self.source.change_stock_update_policy(
            replace(self.source.stock_update_policy, ttl=timedelta(days=1))
        )
        repeat = self.record(
            received_at=self.received_at, source=source.availability_snapshot()
        )
        self.assertIs(repeat, self.availability)
        self.assertEqual(repeat.expires_at, self.received_at + timedelta(hours=2))
        for invalid in (True, -1, "0"):
            with (
                self.subTest(expected_version=invalid),
                self.assertRaises(InvalidSupplierAvailabilityValueError),
            ):
                self.record(expected_version=invalid)
        with self.assertRaises(SupplierAvailabilityVersionConflictError):
            self.record(expected_version=1)
        with self.assertRaises(FrozenInstanceError):
            self.availability.version = 3

    def test_rejects_older_receipt_older_supplier_time_and_equal_time_conflict(
        self,
    ) -> None:
        """Свежая доставка сообщения не позволяет заменить новые данные устаревшей отметкой."""
        changed = replace(self.observation, quantity=Decimal(16))
        for changes in (
            dict(received_at=self.received_at - timedelta(seconds=1)),
            dict(received_at=self.received_at, observation=changed),
            dict(source_updated_at=self.source_updated_at - timedelta(seconds=1)),
            dict(observation=changed),
        ):
            with (
                self.subTest(changes=changes),
                self.assertRaises(SupplierAvailabilityTimeError),
            ):
                self.record(**changes)

    def test_new_poll_with_same_provider_time_can_refresh_unchanged_observation(
        self,
    ) -> None:
        """Более позднее получение тех же данных отличается от точного повтора."""
        updated = self.record()
        self.assertEqual(updated.observation, self.observation)
        self.assertEqual(updated.source_updated_at, self.source_updated_at)
        self.assertEqual(updated.version, 1)
        self.assertEqual(
            updated.expires_at, self.availability.expires_at + timedelta(minutes=30)
        )

    def test_missing_provider_time_uses_received_order(self) -> None:
        """Источники без своей отметки обновляют наблюдение по времени получения."""
        initial = self.create(source_updated_at=None)
        changed = replace(self.observation, quantity=Decimal(16))
        updated = initial.record_observation(
            offer=self.offer.availability_snapshot(),
            source=self.source.availability_snapshot(),
            observation=changed,
            uom=self.offer.base_uom,
            received_at=self.received_at + timedelta(minutes=1),
            expected_version=0,
        )
        self.assertIsNone(updated.source_updated_at)
        self.assertEqual(updated.observation, changed)
        self.assertEqual(updated.version, 1)

    def test_evaluate_exact_ttl_boundary_and_both_stale_rules(self) -> None:
        """В момент истечения срока эффективное значение становится UNKNOWN, исходное сохраняется."""
        expiry = self.availability.expires_at
        fresh = self.availability.evaluate(
            as_of=expiry - timedelta(microseconds=1),
            source=self.source.availability_snapshot(),
        )
        self.assertFalse(fresh.is_stale)
        self.assertEqual(fresh.observation, self.observation)
        self.assertFalse(fresh.automatic_sale_blocked)
        for behavior in StaleStockBehavior:
            with self.subTest(behavior=behavior):
                source = self.source.change_stock_update_policy(
                    replace(
                        self.source.stock_update_policy,
                        ttl=timedelta(days=1),
                        stale_behavior=behavior,
                    )
                )
                stale = self.availability.evaluate(
                    as_of=expiry, source=source.availability_snapshot()
                )
                self.assertTrue(stale.is_stale)
                self.assertIs(
                    stale.observation.availability_type, AvailabilityType.UNKNOWN
                )
                self.assertIs(
                    stale.observation.availability_status, AvailabilityStatus.UNKNOWN
                )
                self.assertIsNone(stale.observation.quantity)
                self.assertIs(
                    stale.automatic_sale_blocked,
                    behavior is StaleStockBehavior.BLOCK_AUTOMATIC_SALE,
                )
        self.assertEqual(self.availability.observation, self.observation)

    def test_evaluation_rejects_foreign_source_and_pre_receipt_time(self) -> None:
        """Оценка текущего наблюдения начинается с его получения и использует его источник."""
        with self.assertRaises(SupplierAvailabilityContextMismatchError):
            self.availability.evaluate(
                as_of=self.received_at,
                source=self.f.source(self.f.supplier).availability_snapshot(),
            )
        with self.assertRaises(SupplierAvailabilityTimeError):
            self.availability.evaluate(
                as_of=self.received_at - timedelta(seconds=1),
                source=self.source.availability_snapshot(),
            )

    def test_restore_checks_saved_values_and_time_without_source(self) -> None:
        """Restore сохраняет срок и проверяет типы, версию и хронологию."""
        self.assertEqual(self.restore(), self.availability)
        for changes in (
            dict(version=True),
            dict(version=-1),
            dict(observation=None),
            dict(supplier_offer_id=self.source.id),
            dict(base_uom="PCS"),
        ):
            with (
                self.subTest(changes=changes),
                self.assertRaises(InvalidSupplierAvailabilityValueError),
            ):
                self.restore(**changes)
        for changes in (
            dict(expires_at=self.received_at),
            dict(received_at=self.received_at.replace(tzinfo=None)),
            dict(source_updated_at=self.source_updated_at.replace(tzinfo=None)),
        ):
            with (
                self.subTest(changes=changes),
                self.assertRaises(SupplierAvailabilityTimeError),
            ):
                self.restore(**changes)
        with self.assertRaises(SupplierAvailabilityTimeError):
            self.create(received_at=datetime.max.replace(tzinfo=UTC))
