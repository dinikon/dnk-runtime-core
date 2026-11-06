"""Отмена выбранных не начатых Allocation без замены и завершение жизненного цикла плана."""

import unittest
from dataclasses import fields, replace
from datetime import timedelta, timezone
from decimal import Decimal, Inexact, Rounded, localcontext
from uuid import uuid4

from test import test_inventory_fulfillment_replanning_domain as replanning_fixture
from test import test_inventory_fulfillment_progress_domain as progress_fixture
from test import test_inventory_shipment_assignment_domain as assignment_fixture
from src.modules.inventory.domain.error import InventoryError
from src.modules.inventory.domain.fulfillment_plan.aggregate import FulfillmentPlan
from src.modules.inventory.domain.fulfillment_plan.entity.fulfillment_allocation import (
    FulfillmentAllocation,
)
from src.modules.inventory.domain.fulfillment_plan.value_object.allocation_id import (
    FulfillmentAllocationIdVO,
)
from src.modules.inventory.domain.fulfillment_plan.value_object.allocation_status import (
    FulfillmentAllocationStatus,
)
from src.modules.inventory.domain.fulfillment_plan.value_object.status import (
    FulfillmentPlanStatus,
)
from src.modules.inventory.domain.value_object.quantity import QuantityVO
from src.modules.inventory.domain.value_object.uom_code import UomCodeVO


class FulfillmentAllocationCancellationDomainTests(unittest.TestCase):
    """Проверяет отмену, повторы, защиту обязательств и историю без текущих внешних данных."""

    def setUp(self) -> None:
        """Готовит план A=3/B=4 и общий контекст уже реализованных резервирования и отгрузки."""
        self.f = replanning_fixture.FulfillmentReplanningDomainTests()
        self.f.setUp()
        self.plan, self.at = self.f.plan, self.f.at
        self.a_id, self.b_id = (row.id for row in self.plan.allocations)

    def cancel(
        self, plan: FulfillmentPlan | None = None, **changes: object
    ) -> FulfillmentPlan:
        """Передаёт выбранные ID, текущую версию и явное неубывающее время."""
        target = self.plan if plan is None else plan
        return target.cancel_allocations(
            **(
                dict(
                    allocation_ids=(self.b_id,),
                    expected_version=target.version,
                    updated_at=max(target.updated_at, self.at),
                )
                | changes
            )
        )

    def progressed(
        self, *, full: bool = False
    ) -> tuple[FulfillmentPlan, progress_fixture.FulfillmentProgressDomainTests]:
        """Регистрирует частичный или полный факт A, затем явно закрывает резерв и снимает подтверждение B."""
        f = progress_fixture.FulfillmentProgressDomainTests()
        f.setUp()
        shipment = f.execute(f.a, {f.a.lines[0].id: "3"}) if full else f.a_partial
        plan = f.register(shipment=shipment)
        closed = f.rf.second_reservation.release_all(
            expected_version=1, updated_at=f.at
        )
        released = plan.release_reservation_confirmations(
            bindings=(f.rf.binding(f.rf.second, closed),),
            reservations=(closed.fulfillment_snapshot(),),
            expected_version=plan.version,
            updated_at=f.at,
        )
        return released, f

    def test_partial_cancellation_keeps_original_quantity_and_other_rows(self) -> None:
        """Отмена B меняет одну версию и не переписывает A или историческое количество B."""
        result = self.cancel()
        self.assertEqual(result.status, FulfillmentPlanStatus.PLANNED)
        self.assertEqual(result.version, self.plan.version + 1)
        self.assertIs(result.allocations[0], self.plan.allocations[0])
        self.assertEqual(
            result.allocations[1],
            replace(
                self.plan.allocations[1],
                status=FulfillmentAllocationStatus.CANCELLED,
                cancelled_at=self.at,
            ),
        )
        self.assertEqual(result.allocations[1].quantity, QuantityVO(Decimal(4)))
        self.assertEqual(
            result.allocations[1].remaining_to_fulfill(), QuantityVO(Decimal(0))
        )
        self.assertEqual(
            result.remaining_to_allocate(self.f.pf.line_ref, demand=self.f.pf.demand),
            QuantityVO(Decimal(4)),
        )
        self.assertEqual(
            self.plan.allocations[1].status, FulfillmentAllocationStatus.PLANNED
        )
        self.f.restore(result)

    def test_cancel_all_planned_rows_closes_plan_once(self) -> None:
        """Отмена всего действующего состава переводит непустую историю в CANCELLED одной версией."""
        result = self.cancel(allocation_ids=(self.a_id, self.b_id))
        self.assertEqual(result.status, FulfillmentPlanStatus.CANCELLED)
        self.assertEqual(result.version, self.plan.version + 1)
        self.assertTrue(
            all(
                row.status is FulfillmentAllocationStatus.CANCELLED
                for row in result.allocations
            )
        )
        self.assertFalse(result.is_fully_confirmed())
        self.f.restore(result)
        with self.assertRaises(InventoryError):
            result.remaining_to_allocate(self.f.pf.line_ref, demand=self.f.pf.demand)

    def test_sequential_cancellation_closes_last_active_row(self) -> None:
        """Последняя отмена учитывает уже сохранённую историю и не оставляет пустой PLANNED."""
        first = self.cancel()
        result = self.cancel(first, allocation_ids=(self.a_id,))
        self.assertEqual(result.status, FulfillmentPlanStatus.CANCELLED)
        self.assertEqual(result.version, first.version + 1)
        self.assertIs(result.allocations[1], first.allocations[1])

    def test_replay_keeps_first_time_and_version(self) -> None:
        """Повтор с более поздним временем не создаёт новую запись отмены."""
        result = self.cancel()
        repeated = self.cancel(result, updated_at=self.at + timedelta(hours=1))
        self.assertIs(repeated, result)
        self.assertEqual(repeated.allocations[1].cancelled_at, self.at)
        self.assertEqual(repeated.updated_at, self.at)

    def test_terminal_cancelled_plan_accepts_exact_replay(self) -> None:
        """Терминальная отмена допускает повтор всего пакета и любой его отменённой части."""
        result = self.cancel(allocation_ids=(self.a_id, self.b_id))
        for ids in ((self.a_id,), (self.b_id,), (self.b_id, self.a_id)):
            with self.subTest(ids=ids):
                self.assertIs(
                    self.cancel(
                        result,
                        allocation_ids=ids,
                        updated_at=self.at + timedelta(minutes=1),
                    ),
                    result,
                )

    def test_mixed_replay_and_new_cancellation_changes_once(self) -> None:
        """Исторический повтор B вместе с новой отменой A изменяет корень ровно один раз."""
        first = self.cancel()
        result = self.cancel(
            first,
            allocation_ids=(self.b_id, self.a_id),
            updated_at=self.at + timedelta(minutes=1),
        )
        self.assertEqual(result.version, first.version + 1)
        self.assertEqual(result.status, FulfillmentPlanStatus.CANCELLED)
        self.assertIs(result.allocations[1], first.allocations[1])
        self.assertEqual(
            result.allocations[0].cancelled_at, self.at + timedelta(minutes=1)
        )

    def test_removing_last_unconfirmed_row_makes_plan_confirmed_and_replay_works(
        self,
    ) -> None:
        """Оставшийся подтверждённый A переводит план в CONFIRMED, где повтор отмены B безопасен."""
        partial = self.f.rf.partial()
        result = self.cancel(partial)
        self.assertEqual(result.status, FulfillmentPlanStatus.CONFIRMED)
        self.assertTrue(result.is_fully_confirmed())
        result.shipment_snapshot().ensure_valid()
        self.assertIs(self.cancel(result), result)
        self.assertIs(result.allocations[0], partial.allocations[0])
        with self.assertRaises(InventoryError):
            self.cancel(result, allocation_ids=(self.a_id,))

    def test_leaving_confirmed_and_planned_rows_keeps_partially_confirmed(self) -> None:
        """Отмена одной из двух свободных строк не теряет подтверждение A."""
        extra = self.f.pf.create_allocation(
            source_ref=self.f.pf.other_ref, quantity=QuantityVO(Decimal(2))
        )
        draft = self.f.pf.add(self.f.pf.add(self.f.pf.one, self.f.rf.second), extra)
        planned = self.f.pf.mark(draft)
        partial = self.f.rf.confirm(
            planned,
            bindings=(self.f.rf.first_binding,),
            reservations=(self.f.rf.first_reservation.fulfillment_snapshot(),),
        )
        result = self.cancel(partial)
        self.assertEqual(result.status, FulfillmentPlanStatus.PARTIALLY_CONFIRMED)
        self.assertIs(result.allocations[0], partial.allocations[0])
        self.assertIs(result.allocations[2], partial.allocations[2])
        result.shipment_snapshot().ensure_valid()

    def test_partial_fulfillment_preserved_then_actual_remaining_completes_plan(
        self,
    ) -> None:
        """Отмена B не превращает его количество в исполнение; оставшиеся 2 с A завершают план."""
        plan, f = self.progressed()
        result = self.cancel(plan, allocation_ids=(f.rf.second.id,))
        self.assertEqual(result.status, FulfillmentPlanStatus.PARTIALLY_FULFILLED)
        self.assertIs(result.allocations[0], plan.allocations[0])
        self.assertEqual(result.allocations[1].fulfilled_qty, QuantityVO(Decimal(0)))
        result.shipment_snapshot().ensure_valid()
        fact = f.execute(f.a_partial, {f.a_partial.lines[0].id: "2"}, at=self.at)
        complete = result.register_shipment(
            fact.fulfillment_snapshot(),
            expected_version=result.version,
            updated_at=self.at,
        )
        self.assertEqual(complete.status, FulfillmentPlanStatus.FULFILLED)
        self.assertEqual(complete.allocations[0].fulfilled_qty, QuantityVO(Decimal(3)))
        self.assertEqual(complete.allocations[1].quantity, QuantityVO(Decimal(4)))
        self.assertEqual(complete.allocations[1].fulfilled_qty, QuantityVO(Decimal(0)))
        self.assertIs(self.cancel(complete, allocation_ids=(f.rf.second.id,)), complete)
        self.assertIs(
            complete.register_shipment(
                fact.fulfillment_snapshot(),
                expected_version=complete.version,
                updated_at=self.at,
            ),
            complete,
        )
        self.f.restore(complete)

    def test_cancelling_last_open_intention_after_full_a_finishes_plan(self) -> None:
        """Если A уже исполнен, отмена ещё не начатого B сразу даёт FULFILLED."""
        plan, f = self.progressed(full=True)
        result = self.cancel(plan, allocation_ids=(f.rf.second.id,))
        self.assertEqual(result.status, FulfillmentPlanStatus.FULFILLED)
        self.assertTrue(result.is_fully_confirmed())
        self.assertIs(result.allocations[0], plan.allocations[0])
        self.assertIs(self.cancel(result, allocation_ids=(f.rf.second.id,)), result)
        with self.assertRaises(InventoryError):
            self.cancel(result, allocation_ids=(result.allocations[0].id,))
        self.f.restore(result)

    def test_closed_reservation_history_survives_cancellation(self) -> None:
        """Снятый резерв сохраняется в отменённой Entity и остаётся занятым для всего плана."""
        released, closed = self.f.close_b(self.f.rf.confirm())
        result = self.cancel(released)
        self.assertEqual(
            result.allocations[1].reservation_releases,
            released.allocations[1].reservation_releases,
        )
        repeated = result.release_reservation_confirmations(
            bindings=(self.f.rf.binding(self.f.rf.second, closed),),
            reservations=(closed.fulfillment_snapshot(),),
            expected_version=result.version,
            updated_at=self.at,
        )
        self.assertIs(repeated, result)
        snapshot = result.shipment_snapshot()
        conflicting = replace(
            snapshot.allocations[0],
            reservation=replace(
                snapshot.allocations[0].reservation, reservation_id=closed.id
            ),
        )
        with self.assertRaises(InventoryError):
            replace(
                snapshot, allocations=(conflicting, snapshot.allocations[1])
            ).ensure_valid()

    def test_history_replay_does_not_cancel_replacement(self) -> None:
        """Запрос по старому B не затрагивает новый C, созданный перепланированием."""
        replanned = self.f.replan()
        self.assertIs(self.cancel(replanned), replanned)
        self.assertIsNone(replanned.allocations[2].cancelled_at)
        self.assertEqual(
            replanned.allocations[2].status, FulfillmentAllocationStatus.PLANNED
        )

    def test_terminal_legacy_cancel_allows_only_history_replay(self) -> None:
        """Старый cancel() сохраняет PLANNED-строки: их нельзя менять через терминальный корень."""
        replanned = self.f.replan()
        terminal = replanned.cancel(
            expected_version=replanned.version, updated_at=self.at
        )
        self.assertIs(self.cancel(terminal), terminal)
        for ids in (
            (self.a_id,),
            (replanned.allocations[2].id,),
            (self.b_id, self.a_id),
        ):
            with self.subTest(ids=ids), self.assertRaises(InventoryError):
                self.cancel(terminal, allocation_ids=ids)
        self.assertIs(terminal.allocations[0], replanned.allocations[0])
        self.assertEqual(terminal.status, FulfillmentPlanStatus.CANCELLED)

    def test_current_context_is_not_required_for_cancellation(self) -> None:
        """Отмена намерения не зависит от текущего спроса, активности склада или нового шага товара."""
        # Передаются только собственные ID, версия и время: внешних снимков в контракте нет.
        row = replace(self.plan.allocations[1], quantity=QuantityVO(Decimal(5)))
        stale = self.f.restore(self.plan, allocations=(self.plan.allocations[0], row))
        result = self.cancel(stale)
        self.assertEqual(result.status, FulfillmentPlanStatus.PLANNED)
        self.assertEqual(result.allocations[1].quantity, QuantityVO(Decimal(5)))

    def test_empty_raw_duplicate_unknown_ids_and_draft_are_rejected(self) -> None:
        """Нужны непустой tuple собственных уникальных ID и зафиксированный план."""
        for ids in (
            (),
            [],
            [self.b_id],
            ("raw",),
            (object(),),
            (self.b_id, self.b_id),
            (FulfillmentAllocationIdVO(uuid4()),),
        ):
            with self.subTest(ids=ids), self.assertRaises(InventoryError):
                self.cancel(allocation_ids=ids)
        with self.assertRaises(InventoryError):
            self.cancel(self.f.pf.one, allocation_ids=(self.a_id,))

    def test_expected_version_and_time_are_checked_even_for_replay(self) -> None:
        """Повтор не обходит проверку строгой версии и явного неубывающего aware-времени."""
        result = self.cancel()
        for plan in (self.plan, result):
            for changes in (
                dict(expected_version=True),
                dict(expected_version=-1),
                dict(expected_version=plan.version - 1),
                dict(updated_at=plan.updated_at - timedelta(seconds=1)),
                dict(updated_at=self.at.replace(tzinfo=None)),
                dict(updated_at="now"),
            ):
                with (
                    self.subTest(plan=plan.status, changes=changes),
                    self.assertRaises(InventoryError),
                ):
                    self.cancel(plan, **changes)
        normalized = self.cancel(
            updated_at=self.at.astimezone(timezone(timedelta(hours=3)))
        )
        self.assertEqual(normalized.updated_at, self.at)
        self.assertEqual(
            normalized.allocations[1].cancelled_at.utcoffset(), timedelta(0)
        )

    def test_active_reserve_must_be_released_before_cancellation(self) -> None:
        """Подтверждённая строка не отменяется автоматически вместе с удержанием."""
        partial = self.f.rf.partial()
        with self.assertRaises(InventoryError):
            self.cancel(partial, allocation_ids=(self.a_id,))
        self.assertIsNotNone(partial.allocations[0].reservation)

    def test_assigned_draft_and_confirmed_shipment_are_protected(self) -> None:
        """Назначение Shipment блокирует отмену Allocation до отмены черновика и снятия назначения."""
        f = assignment_fixture.ShipmentAssignmentDomainTests()
        f.setUp()
        with self.assertRaises(InventoryError):
            self.cancel(f.assigned, allocation_ids=(f.assigned.allocations[0].id,))
        f.confirm()
        with self.assertRaises(InventoryError):
            self.cancel(f.assigned, allocation_ids=(f.assigned.allocations[0].id,))

    def test_cancel_draft_release_assignment_and_reservation_then_cancel_intention(
        self,
    ) -> None:
        """Полная штатная подготовка снимает внешние привязки до отмены собственного намерения."""
        f = assignment_fixture.ShipmentAssignmentDomainTests()
        f.setUp()
        unassigned = f.release()
        reserve = f.f.f.first_reservation
        closed = reserve.release_all(expected_version=reserve.version, updated_at=f.at)
        released = unassigned.release_reservation_confirmations(
            bindings=(f.f.f.binding(unassigned.allocations[0], closed),),
            reservations=(closed.fulfillment_snapshot(),),
            expected_version=unassigned.version,
            updated_at=f.at,
        )
        result = self.cancel(released, allocation_ids=(released.allocations[0].id,))
        self.assertEqual(result.status, FulfillmentPlanStatus.CONFIRMED)
        self.assertIsNone(result.allocations[0].shipment_assignment)
        self.assertEqual(
            result.allocations[0].status, FulfillmentAllocationStatus.CANCELLED
        )
        self.assertEqual(
            result.allocations[0].reservation_releases[0].confirmation.reservation_id,
            reserve.id,
        )

    def test_registered_partial_and_full_execution_cannot_be_cancelled(self) -> None:
        """Ни частичный факт, ни полностью исполненная строка не превращаются в отмену."""
        for full in (False, True):
            plan, f = self.progressed(full=full)
            with self.subTest(full=full), self.assertRaises(InventoryError):
                self.cancel(plan, allocation_ids=(plan.allocations[0].id,))
            self.assertIsNotNone(plan.allocations[0].shipment_progress)

    def test_invalid_last_row_preserves_whole_batch(self) -> None:
        """Отмена свободного B и запрещённого A не оставляет частично применённый пакет."""
        partial = self.f.rf.partial()
        with self.assertRaises(InventoryError):
            self.cancel(partial, allocation_ids=(self.b_id, self.a_id))
        self.assertEqual(
            partial.allocations[1].status, FulfillmentAllocationStatus.PLANNED
        )
        self.assertIsNone(partial.allocations[1].cancelled_at)
        self.assertIsNotNone(partial.allocations[0].reservation)

    def test_invalid_last_id_does_not_apply_first_cancellation(self) -> None:
        """Сначала проверяется весь набор выбранных ID."""
        with self.assertRaises(InventoryError):
            self.cancel(allocation_ids=(self.b_id, FulfillmentAllocationIdVO(uuid4())))
        self.assertTrue(all(row.cancelled_at is None for row in self.plan.allocations))

    def test_replanning_cannot_select_already_cancelled_row(self) -> None:
        """Локальный повтор отмены не позволяет перепланировать старую историческую строку заново."""
        result = self.cancel()
        with self.assertRaises(InventoryError):
            self.f.replan(result)
        self.assertEqual(len(result.allocations), 2)

    def test_cancelled_row_cannot_be_confirmed_assigned_or_executed(self) -> None:
        """Терминальный локальный статус защищён во всех последующих командах Entity."""
        row = self.cancel().allocations[1]
        confirmed = self.f.rf.confirm().allocations[1]
        assignment = assignment_fixture.ShipmentAssignmentDomainTests()
        assignment.setUp()
        progress, _ = self.progressed()
        for operation in (
            lambda: row.confirm_reservation(confirmed.reservation),
            lambda: row.assign_shipment(
                assignment.assigned.allocations[0].shipment_assignment
            ),
            lambda: row.register_shipment_progress(
                fulfilled_qty=QuantityVO(Decimal(1)),
                progress=progress.allocations[0].shipment_progress,
            ),
        ):
            with self.assertRaises(InventoryError):
                operation()

    def test_entity_repeat_keeps_first_timestamp_and_validates_time(self) -> None:
        """Локальная отмена идемпотентна, но не допускает наивное или более раннее время."""
        row = self.plan.allocations[1].cancel_unstarted(cancelled_at=self.at)
        self.assertIs(
            row.cancel_unstarted(cancelled_at=self.at + timedelta(days=1)), row
        )
        self.assertEqual(row.cancelled_at, self.at)
        for value in (
            self.at - timedelta(seconds=1),
            self.at.replace(tzinfo=None),
            "now",
        ):
            with self.subTest(value=value), self.assertRaises(InventoryError):
                row.cancel_unstarted(cancelled_at=value)

    def test_cancellation_cannot_precede_last_reserve_release(self) -> None:
        """История закрытых резервов должна предшествовать отмене намерения."""
        released, _ = self.f.close_b(self.f.rf.confirm())
        row = released.allocations[1]
        with self.assertRaises(InventoryError):
            row.cancel_unstarted(cancelled_at=self.at - timedelta(seconds=1))
        result = self.cancel(released)
        self.assertEqual(
            result.allocations[1].cancelled_at, row.reservation_releases[-1].released_at
        )

    def test_restore_keeps_terminal_history_without_current_context(self) -> None:
        """Восстановление собственного состава проверяет даты и статусы, не свежие справочники."""
        result = self.cancel(allocation_ids=(self.a_id, self.b_id))
        self.assertEqual(self.f.restore(result), result)
        row = result.allocations[1]
        values = {field.name: getattr(row, field.name) for field in fields(row)}
        values["identifier"] = values.pop("id")
        self.assertEqual(FulfillmentAllocation.restore(**values), row)
        with self.assertRaises(InventoryError):
            self.f.restore(result, updated_at=self.at - timedelta(seconds=1))
        with self.assertRaises(InventoryError):
            self.f.restore(result, status=FulfillmentPlanStatus.DRAFT)

    def test_fractional_cancellation_does_not_round_or_reinterpret_quantity(
        self,
    ) -> None:
        """Отмена не выполняет арифметику исторического количества и сохраняет его точное значение."""
        rows = tuple(
            replace(
                row,
                base_uom=UomCodeVO("KG"),
                quantity=QuantityVO(Decimal("123.456789")),
            )
            for row in self.plan.allocations
        )
        plan = self.f.restore(self.plan, allocations=rows)
        with localcontext() as ctx:
            ctx.prec = 2
            ctx.traps[Inexact] = True
            ctx.traps[Rounded] = True
            result = self.cancel(plan)
        self.assertEqual(
            result.allocations[1].quantity, QuantityVO(Decimal("123.456789"))
        )
        self.assertEqual(
            result.allocations[1].remaining_to_fulfill(), QuantityVO(Decimal(0))
        )


if __name__ == "__main__":
    unittest.main()
