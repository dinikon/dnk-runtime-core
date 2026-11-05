"""План полной и частичной инвентаризации: область, подтверждение, история и защита переходов."""

import unittest
from dataclasses import FrozenInstanceError, replace
from datetime import UTC, datetime, timedelta, timezone
from uuid import UUID, uuid4

from src.modules.inventory.domain.inventory_count.aggregate import InventoryCount
from src.modules.inventory.domain.inventory_count.error import (
    InvalidCountScopeError,
    InvalidInventoryCountValueError,
    InventoryCountContextMismatchError,
    InventoryCountStatusError,
    InventoryCountTimeError,
    InventoryCountVersionConflictError,
)
from src.modules.inventory.domain.inventory_count.value_object.count_type import (
    CountType,
)
from src.modules.inventory.domain.inventory_count.value_object.identifier import (
    InventoryCountIdVO,
)
from src.modules.inventory.domain.inventory_count.value_object.scope import CountScopeVO
from src.modules.inventory.domain.inventory_count.value_object.status import (
    InventoryCountStatus,
)
from src.modules.inventory.domain.policy.inventory_count_confirmation import (
    InventoryCountConfirmationPolicy,
)
from src.modules.inventory.domain.stock_location.error import (
    InvalidStockLocationSnapshotError,
    StockLocationInactiveError,
    StockLocationWarehouseMismatchError,
)
from src.modules.inventory.domain.stock_location.snapshot import StockLocationSnapshot
from src.modules.inventory.domain.stock_location.value_object.identifier import (
    StockLocationIdVO,
)
from src.modules.inventory.domain.stock_location.value_object.location_type import (
    LocationType,
)
from src.modules.inventory.domain.value_object.stock_owner_id import StockOwnerIdVO
from src.modules.inventory.domain.warehouse.error import (
    InvalidWarehouseSnapshotError,
    WarehouseInactiveError,
)
from src.modules.inventory.domain.warehouse.snapshot import WarehouseSnapshot
from src.modules.inventory.domain.warehouse.value_object.identifier import WarehouseIdVO
from src.modules.shared.domain.domain_error import EntityIdTypeError


class InventoryCountDomainTests(unittest.TestCase):
    """Проверяет небольшой агрегат плана без ведомостей, учётного снимка и складских движений."""

    def setUp(self) -> None:
        """Готовит склад без основной локации и два независимых адреса одного владельца."""
        self.time = datetime(2026, 11, 5, 12, tzinfo=UTC)
        self.warehouse = WarehouseSnapshot(WarehouseIdVO(uuid4()), True, None)
        self.owner = StockOwnerIdVO(uuid4())
        self.first = StockLocationSnapshot(
            StockLocationIdVO(UUID(int=1)),
            self.warehouse.id,
            LocationType.STORAGE,
            True,
        )
        self.second = StockLocationSnapshot(
            StockLocationIdVO(UUID(int=2)),
            self.warehouse.id,
            LocationType.QUARANTINE,
            True,
        )
        self.full = CountScopeVO(CountType.FULL, ())
        self.partial = CountScopeVO(CountType.PARTIAL, (self.first.id, self.second.id))

    def create(self, **changes: object) -> InventoryCount:
        """Создаёт новый полный черновик с возможностью явно заменить вход сценария."""
        return InventoryCount.create(
            **(
                dict(
                    identifier=InventoryCountIdVO(uuid4()),
                    warehouse=self.warehouse,
                    owner_id=self.owner,
                    scope=self.full,
                    created_at=self.time,
                )
                | changes
            )
        )

    def restore(self, reference: InventoryCount, **changes: object) -> InventoryCount:
        """Восстанавливает весь сохранённый собственный состав без снимков склада или локаций."""
        return InventoryCount.restore(
            **(
                dict(
                    identifier=reference.id,
                    warehouse_id=reference.warehouse_id,
                    owner_id=reference.owner_id,
                    scope=reference.scope,
                    status=reference.status,
                    baseline=reference.baseline,
                    result=reference.result,
                    created_at=reference.created_at,
                    updated_at=reference.updated_at,
                    version=reference.version,
                )
                | changes
            )
        )

    def confirm(self, count: InventoryCount, **changes: object) -> InventoryCount:
        """Подтверждает по текущей версии, времени и ровно выбранным адресам."""
        return count.confirm(
            **(
                dict(
                    expected_version=count.version,
                    warehouse=self.warehouse,
                    locations=(
                        ()
                        if count.scope.count_type is CountType.FULL
                        else (self.first, self.second)
                    ),
                    updated_at=self.time,
                )
                | changes
            )
        )

    def test_scope_normalizes_order_and_has_value_equality_and_hash(self) -> None:
        """Порядок выбора адресов не меняет область или её хеш; состав хранится канонически."""
        reverse = CountScopeVO(CountType.PARTIAL, (self.second.id, self.first.id))
        self.assertEqual(reverse, self.partial)
        self.assertEqual(hash(reverse), hash(self.partial))
        self.assertEqual(reverse.location_ids, (self.first.id, self.second.id))

    def test_scope_rejects_invalid_modes_shapes_duplicates_and_identifier_types(
        self,
    ) -> None:
        """FULL не перечисляет адреса; PARTIAL не пуст; строки, списки и чужие ID недопустимы."""
        for kind, identifiers in (
            ("FULL", ()),
            (None, ()),
            (CountType.FULL, (self.first.id,)),
            (CountType.PARTIAL, ()),
            (CountType.PARTIAL, [self.first.id]),
            (CountType.PARTIAL, (self.first.id, self.first.id)),
            (CountType.PARTIAL, (self.first.id.uuid,)),
            (CountType.PARTIAL, (self.warehouse.id,)),
        ):
            with self.subTest(kind=kind, identifiers=identifiers):
                with self.assertRaises(InvalidCountScopeError):
                    CountScopeVO(kind, identifiers)

    def test_count_identifier_rejects_raw_string_and_another_specialized_id(
        self,
    ) -> None:
        """Идентификатор инвентаризации сохраняет номинальную UUID-типизацию проекта."""
        with self.assertRaises(EntityIdTypeError):
            InventoryCountIdVO("not-uuid")
        with self.assertRaises(EntityIdTypeError):
            InventoryCountIdVO.from_value(self.warehouse.id)

    def test_create_full_draft_and_confirm_without_default_location(self) -> None:
        """Полную проверку можно запланировать и подтвердить без перечисления адресов склада."""
        draft = self.create()
        confirmed = self.confirm(draft)
        self.assertEqual((draft.status, draft.version), (InventoryCountStatus.DRAFT, 0))
        self.assertEqual(
            (confirmed.status, confirmed.version), (InventoryCountStatus.CONFIRMED, 1)
        )
        self.assertEqual(confirmed.id, draft.id)
        self.assertEqual(confirmed.warehouse_id, self.warehouse.id)
        self.assertEqual(confirmed.owner_id, self.owner)
        self.assertEqual(confirmed.scope, self.full)

    def test_partial_scope_can_be_drafted_before_locations_are_checked(self) -> None:
        """Черновик хранит ID; принадлежность и активность адресов повторно проверяются при подтверждении."""
        draft = self.create(scope=self.partial)
        confirmed = self.confirm(draft, locations=(self.second, self.first))
        self.assertEqual(confirmed.scope, self.partial)
        self.assertEqual(draft.version, 0)
        with self.assertRaises(InventoryCountContextMismatchError):
            self.confirm(draft, locations=())

    def test_change_scope_preserves_identity_and_increments_version_once(self) -> None:
        """Меняется только область черновика, время и версия; склад и владелец фиксированы."""
        draft = self.create()
        later = self.time + timedelta(minutes=1)
        changed = draft.change_scope(self.partial, expected_version=0, updated_at=later)
        self.assertEqual(changed.version, 1)
        self.assertEqual(changed.scope, self.partial)
        self.assertEqual(changed.updated_at, later)
        self.assertEqual(
            (changed.id, changed.warehouse_id, changed.owner_id, changed.created_at),
            (draft.id, draft.warehouse_id, draft.owner_id, draft.created_at),
        )
        self.assertEqual(draft.scope, self.full)
        restored_full = changed.change_scope(
            self.full, expected_version=1, updated_at=later
        )
        self.assertEqual(restored_full.version, 2)
        self.assertEqual(restored_full.scope, self.full)

    def test_equal_scope_is_noop_even_with_reordered_ids_and_later_time(self) -> None:
        """Равная область не обновляет время или версию после обязательных проверок."""
        draft = self.create(scope=self.partial)
        reordered = CountScopeVO(CountType.PARTIAL, (self.second.id, self.first.id))
        result = draft.change_scope(
            reordered, expected_version=0, updated_at=self.time + timedelta(hours=1)
        )
        self.assertIs(result, draft)
        self.assertEqual(result.updated_at, self.time)

    def test_noop_does_not_bypass_version_time_or_status_checks(self) -> None:
        """Даже равная область требует актуальную версию, допустимое время и черновик."""
        draft = self.create()
        with self.assertRaises(InventoryCountVersionConflictError):
            draft.change_scope(self.full, expected_version=1, updated_at=self.time)
        with self.assertRaises(InventoryCountTimeError):
            draft.change_scope(
                self.full,
                expected_version=0,
                updated_at=self.time - timedelta(seconds=1),
            )
        confirmed = self.confirm(draft)
        with self.assertRaises(InventoryCountStatusError):
            confirmed.change_scope(self.full, expected_version=1, updated_at=self.time)

    def test_cancel_keeps_scope_and_requires_no_current_external_context(self) -> None:
        """Отмена сохраняет область и возможна без повторной загрузки ставшего неактивным склада."""
        draft = self.create(scope=self.partial)
        cancelled = draft.cancel(expected_version=0, updated_at=self.time)
        self.assertEqual(cancelled.status, InventoryCountStatus.CANCELLED)
        self.assertEqual(cancelled.scope, draft.scope)
        self.assertEqual(cancelled.version, 1)
        self.assertEqual(draft.status, InventoryCountStatus.DRAFT)

    def test_confirmed_and_cancelled_reject_all_transitions(self) -> None:
        """Подтверждение и отмена завершают жизненный цикл первого планового среза."""
        draft = self.create()
        for count in (
            self.confirm(draft),
            draft.cancel(expected_version=0, updated_at=self.time),
        ):
            with self.subTest(status=count.status):
                with self.assertRaises(InventoryCountStatusError):
                    self.confirm(count)
                with self.assertRaises(InventoryCountStatusError):
                    count.cancel(expected_version=count.version, updated_at=self.time)
                with self.assertRaises(InventoryCountStatusError):
                    count.change_scope(
                        self.partial,
                        expected_version=count.version,
                        updated_at=self.time,
                    )

    def test_each_transition_checks_strict_expected_and_current_version(self) -> None:
        """bool, отрицательные и нецелые версии отклоняются до увеличения версии агрегата."""
        draft = self.create()
        for bad in (True, False, -1, 0.0, "0", None):
            for action in ("scope", "confirm", "cancel"):
                with self.subTest(bad=bad, action=action):
                    with self.assertRaises(InvalidInventoryCountValueError):
                        if action == "scope":
                            draft.change_scope(
                                self.partial, expected_version=bad, updated_at=self.time
                            )
                        elif action == "confirm":
                            self.confirm(draft, expected_version=bad)
                        else:
                            draft.cancel(expected_version=bad, updated_at=self.time)
            forged = replace(draft, version=bad)
            with self.assertRaises(InvalidInventoryCountValueError):
                forged.cancel(expected_version=0, updated_at=self.time)

    def test_all_transitions_reject_stale_version_without_mutating_draft(self) -> None:
        """Ни один переход не принимает чужую версию и не меняет исходный объект при отказе."""
        draft = self.create()
        with self.assertRaises(InventoryCountVersionConflictError):
            draft.change_scope(self.partial, expected_version=2, updated_at=self.time)
        with self.assertRaises(InventoryCountVersionConflictError):
            self.confirm(draft, expected_version=2)
        with self.assertRaises(InventoryCountVersionConflictError):
            draft.cancel(expected_version=2, updated_at=self.time)
        self.assertEqual(
            (draft.scope, draft.status, draft.version),
            (self.full, InventoryCountStatus.DRAFT, 0),
        )

    def test_create_and_confirm_require_active_valid_warehouse_snapshots(self) -> None:
        """Склад проверяется при создании и заново при подтверждении; корень или произвольный объект не подходит."""
        draft = self.create()
        for warehouse, error in (
            (replace(self.warehouse, is_active=False), WarehouseInactiveError),
            (replace(self.warehouse, is_active=1), InvalidWarehouseSnapshotError),
            (replace(self.warehouse, id=self.owner), InvalidWarehouseSnapshotError),
            (object(), InvalidWarehouseSnapshotError),
        ):
            with self.subTest(warehouse=warehouse):
                with self.assertRaises(error):
                    self.create(warehouse=warehouse)
                with self.assertRaises(error):
                    self.confirm(draft, warehouse=warehouse)
        with self.assertRaises(InventoryCountContextMismatchError):
            self.confirm(
                draft, warehouse=replace(self.warehouse, id=WarehouseIdVO(uuid4()))
            )

    def test_partial_confirm_requires_exact_location_set(self) -> None:
        """Пропуски, лишние адреса, дубли и список вместо tuple не принимаются."""
        draft = self.create(scope=self.partial)
        extra = replace(self.first, id=StockLocationIdVO(uuid4()))
        for locations in (
            (),
            (self.first,),
            (self.first, self.first),
            (self.first, self.second, extra),
            [self.first, self.second],
        ):
            with self.subTest(locations=locations):
                with self.assertRaises(InventoryCountContextMismatchError):
                    self.confirm(draft, locations=locations)
        self.assertEqual(draft.version, 0)

    def test_full_confirm_rejects_unrequested_location_snapshots(self) -> None:
        """FULL означает весь склад и не принимает частичный список как доказательство полной области."""
        with self.assertRaises(InventoryCountContextMismatchError):
            self.confirm(self.create(), locations=(self.first,))

    def test_partial_confirm_checks_membership_activity_and_runtime_types(self) -> None:
        """Выбранные адреса должны быть корректными активными снимками того же склада."""
        draft = self.create(scope=self.partial)
        for first, error in (
            (
                replace(self.first, warehouse_id=WarehouseIdVO(uuid4())),
                StockLocationWarehouseMismatchError,
            ),
            (replace(self.first, is_active=False), StockLocationInactiveError),
            (replace(self.first, is_active=1), InvalidStockLocationSnapshotError),
            (
                replace(self.first, location_type="STORAGE"),
                InvalidStockLocationSnapshotError,
            ),
            (self.first.id, InvalidStockLocationSnapshotError),
        ):
            with self.subTest(first=first):
                with self.assertRaises(error):
                    self.confirm(draft, locations=(first, self.second))

    def test_count_scope_does_not_filter_by_sellable_location_type(self) -> None:
        """Адреса приёмки, отгрузки, карантина и транзитного учёта не отбрасываются правилом доступности продаж."""
        for kind in LocationType:
            with self.subTest(kind=kind):
                draft = self.create(
                    scope=CountScopeVO(CountType.PARTIAL, (self.first.id,))
                )
                result = self.confirm(
                    draft, locations=(replace(self.first, location_type=kind),)
                )
                self.assertEqual(result.status, InventoryCountStatus.CONFIRMED)

    def test_restore_preserves_history_without_current_warehouse_or_locations(
        self,
    ) -> None:
        """Восстановление подтверждённой или отменённой истории не требует текущей активности справочников."""
        draft = self.create(scope=self.partial)
        for reference in (
            draft,
            self.confirm(draft),
            draft.cancel(expected_version=0, updated_at=self.time),
        ):
            with self.subTest(status=reference.status):
                self.assertEqual(self.restore(reference), reference)
        restored = self.restore(draft, version=7, status=InventoryCountStatus.CONFIRMED)
        self.assertEqual((restored.scope, restored.version), (self.partial, 7))

    def test_create_and_restore_reject_invalid_own_fields(self) -> None:
        """Типизированная область, владелец, идентичность, статус и строгая версия обязательны."""
        draft = self.create()
        for field, value in (
            ("identifier", self.warehouse.id),
            ("owner_id", None),
            ("scope", None),
        ):
            with self.subTest(field=field):
                with self.assertRaises(InvalidInventoryCountValueError):
                    self.create(**{field: value})
        for field, value in (
            ("identifier", self.warehouse.id),
            ("warehouse_id", self.owner),
            ("owner_id", self.warehouse.id),
            ("scope", object()),
            ("status", "DRAFT"),
            ("version", True),
            ("version", -1),
        ):
            with self.subTest(field=field):
                with self.assertRaises(InvalidInventoryCountValueError):
                    self.restore(draft, **{field: value})
        with self.assertRaises(InvalidInventoryCountValueError):
            draft.change_scope(None, expected_version=0, updated_at=self.time)

    def test_nested_scope_is_revalidated_at_domain_boundaries(self) -> None:
        """Вход с повреждённым собственным составом VO не проходит фабрики и прямой вызов политики."""
        invalid = CountScopeVO(CountType.PARTIAL, (self.first.id,))
        object.__setattr__(invalid, "location_ids", ())
        with self.assertRaises(InvalidCountScopeError):
            self.create(scope=invalid)
        with self.assertRaises(InvalidCountScopeError):
            self.create().change_scope(
                invalid, expected_version=0, updated_at=self.time
            )
        with self.assertRaises(InvalidCountScopeError):
            InventoryCountConfirmationPolicy.ensure_confirmable(
                warehouse_id=self.warehouse.id,
                warehouse=self.warehouse,
                scope=invalid,
                locations=(),
            )

    def test_policy_direct_calls_validate_warehouse_id_and_scope(self) -> None:
        """Чистая политика защищает собственный публичный контракт без предварительного вызова корня."""
        with self.assertRaises(InventoryCountContextMismatchError):
            InventoryCountConfirmationPolicy.ensure_warehouse(
                warehouse_id=self.owner, warehouse=self.warehouse
            )
        with self.assertRaises(InvalidCountScopeError):
            InventoryCountConfirmationPolicy.ensure_confirmable(
                warehouse_id=self.warehouse.id,
                warehouse=self.warehouse,
                scope="FULL",
                locations=(),
            )

    def test_aware_times_normalize_to_utc_and_equal_instants_are_allowed(self) -> None:
        """Другой часовой пояс не меняет момент; каждая сохранённая дата нормализована в UTC."""
        local = self.time.astimezone(timezone(timedelta(hours=2)))
        draft = self.create(created_at=local)
        confirmed = self.confirm(draft, updated_at=local)
        restored = self.restore(confirmed, created_at=local, updated_at=local)
        self.assertEqual(restored.created_at, self.time)
        self.assertIs(restored.created_at.tzinfo, UTC)
        self.assertIs(restored.updated_at.tzinfo, UTC)

    def test_naive_invalid_and_regressing_times_are_rejected_on_all_paths(self) -> None:
        """Без часового пояса или с убыванием времени нельзя создать, восстановить или изменить план."""
        draft = self.create()
        for bad in (None, "now", self.time.replace(tzinfo=None)):
            with self.subTest(bad=bad):
                with self.assertRaises(InventoryCountTimeError):
                    self.create(created_at=bad)
                with self.assertRaises(InventoryCountTimeError):
                    self.restore(draft, updated_at=bad)
                with self.assertRaises(InventoryCountTimeError):
                    draft.cancel(expected_version=0, updated_at=bad)
        past = self.time - timedelta(seconds=1)
        with self.assertRaises(InventoryCountTimeError):
            self.restore(draft, updated_at=past)
        for action in ("scope", "confirm", "cancel"):
            with self.subTest(action=action):
                with self.assertRaises(InventoryCountTimeError):
                    if action == "scope":
                        draft.change_scope(
                            self.partial, expected_version=0, updated_at=past
                        )
                    elif action == "confirm":
                        self.confirm(draft, updated_at=past)
                    else:
                        draft.cancel(expected_version=0, updated_at=past)

    def test_aggregate_and_scope_are_immutable(self) -> None:
        """Прямое присваивание не меняет ни план, ни область проверки."""
        draft = self.create()
        with self.assertRaises(FrozenInstanceError):
            draft.status = InventoryCountStatus.CONFIRMED
        with self.assertRaises(FrozenInstanceError):
            draft.scope.location_ids = (self.first.id,)


if __name__ == "__main__":
    unittest.main()
