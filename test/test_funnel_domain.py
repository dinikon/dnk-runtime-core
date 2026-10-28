"""Правила полного определения воронки и собственных значений стадий."""

import unittest
from dataclasses import replace
from datetime import UTC, datetime
from uuid import uuid4
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.funnel.domain.aggregate import Funnel
from src.modules.funnel.domain.stage import Stage
from src.modules.funnel.domain.error import FunnelError, FunnelConflictError
from src.modules.funnel.domain.value_object.stage_color import StageColorVO


class FunnelDomainTests(unittest.TestCase):
    def setUp(self) -> None:
        self.actor = EntityIdVO(uuid4())
        self.now = datetime.now(UTC)
        self.stages = Funnel.default_stages(
            tuple(EntityIdVO(uuid4()) for _ in range(4))
        )
        self.funnel = Funnel.create(
            funnel_id=EntityIdVO(uuid4()),
            model_key="crm.deal",
            name=" Продажи ",
            stages=self.stages,
            actor_id=self.actor,
            now=self.now,
        )

    def save(self, stages: tuple[Stage, ...], revision: int = 1) -> None:
        self.funnel.replace_process(
            name="Продажи",
            stages=stages,
            expected_revision=revision,
            actor_id=self.actor,
            now=self.now,
        )

    def test_template_and_normalization(self) -> None:
        self.assertEqual(
            [s.kind.value for s in self.stages],
            ["in_progress", "in_progress", "won", "lost"],
        )
        self.assertEqual(StageColorVO("#aBc123").value, "#ABC123")
        for invalid in ("red", "#fff", "#11223344", "112233", "#GG0000", " #112233"):
            with self.subTest(color=invalid), self.assertRaises(FunnelError):
                StageColorVO(invalid)

    def test_invalid_compositions_are_atomic(self) -> None:
        extra_won = Stage.create(stage_id=EntityIdVO(uuid4()), name="Успех", kind="won")
        for stages in (
            self.stages[:2],
            self.stages[:3],
            self.stages[2:],
            (*self.stages[:3], extra_won, self.stages[3]),
            tuple(reversed(self.stages)),
            (*self.stages, self.stages[3]),
        ):
            with self.subTest(stages=stages), self.assertRaises(FunnelError):
                self.save(stages)
            self.assertEqual(self.funnel.stages, self.stages)
            self.assertEqual(self.funnel.revision, 1)

    def test_existing_kind_and_won_identity_are_immutable(self) -> None:
        changed = replace(self.stages[1], kind=self.stages[3].kind)
        with self.assertRaises(FunnelError):
            self.save((self.stages[0], self.stages[2], changed, self.stages[3]))
        other = Stage.create(
            stage_id=EntityIdVO(uuid4()), name="Другой успех", kind="won"
        )
        with self.assertRaises(FunnelError):
            self.save((*self.stages[:2], other, self.stages[3]))

    def test_remove_initial_and_reorder_preserve_ids(self) -> None:
        self.save(self.stages[1:])
        self.assertEqual(self.funnel.select_stage("crm.deal").id, self.stages[1].id)
        self.assertEqual(self.funnel.revision, 2)
        self.save(self.stages[1:], 2)
        self.assertEqual(self.funnel.revision, 2)
        with self.assertRaises(FunnelConflictError):
            self.save(self.stages, 1)

    def test_last_work_and_lost_can_be_replaced_together(self) -> None:
        work = Stage.create(stage_id=EntityIdVO(uuid4()), name="Старт")
        lost = Stage.create(stage_id=EntityIdVO(uuid4()), name="Отказ", kind="lost")
        self.save((work, self.stages[2], lost))
        self.assertEqual(len(self.funnel.stages), 3)

    def test_maximum_stage_count(self) -> None:
        """Лимит учитывает стадии всех групп."""
        extra = tuple(
            Stage.create(stage_id=EntityIdVO(uuid4()), name="Отказ", kind="lost")
            for _ in range(46)
        )
        self.save((*self.stages, *extra))
        self.assertEqual(len(self.funnel.stages), 50)
        with self.assertRaises(FunnelError):
            self.save(
                (
                    *self.funnel.stages,
                    Stage.create(
                        stage_id=EntityIdVO(uuid4()), name="Лишняя", kind="lost"
                    ),
                ),
                2,
            )
        self.assertEqual(len(self.funnel.stages), 50)
