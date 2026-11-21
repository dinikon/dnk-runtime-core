from src.modules.inventory.domain.policy.stock_issue_valuation import (
    StockIssueValuationPolicy,
)
from src.modules.inventory.domain.policy.stock_posting import StockPostingPolicy
from src.modules.inventory.domain.stock_location.snapshot import StockLocationSnapshot
from src.modules.inventory.domain.stock_position.snapshot import StockPositionSnapshot
from src.modules.inventory.domain.stock_posting.error import (
    InvalidStockPostingFifoPlanError,
)
from src.modules.inventory.domain.stock_posting.fifo_plan_snapshot import (
    StockIssueFifoPlanSnapshot,
)
from src.modules.inventory.domain.stock_posting.snapshot import StockPostingSnapshot
from src.modules.inventory.domain.stock_posting.value_object.operation_type import (
    StockOperationType,
)
from src.modules.inventory.domain.valuation_layer.fifo_snapshot import (
    ValuationLayerFifoSnapshot,
)


class StockPostingFifoPolicy:
    """Строит FIFO-основание всех записей ISSUE по точному физическому контексту без изменения слоёв."""

    @staticmethod
    def _ensure_source(posting: StockPostingSnapshot) -> None:
        """Требует валидный снимок обычного расходного проведения без компенсации."""
        if not isinstance(posting, StockPostingSnapshot):
            raise InvalidStockPostingFifoPlanError(
                "Нужен снимок физического проведения."
            )
        posting.ensure_valid()
        if (
            posting.operation_type is not StockOperationType.ISSUE
            or posting.reversal_of_id is not None
        ):
            raise InvalidStockPostingFifoPlanError(
                "Полный FIFO-план строится только для обычного ISSUE."
            )

    @staticmethod
    def build_plans(
        *,
        posting: StockPostingSnapshot,
        candidates: tuple[ValuationLayerFifoSnapshot, ...],
        positions: tuple[StockPositionSnapshot, ...],
        locations: tuple[StockLocationSnapshot, ...],
    ) -> tuple[StockIssueFifoPlanSnapshot, ...]:
        """Распределяет полный пул по исходным позициям и строит все планы в порядке Ledger или отклоняет весь запрос."""
        StockPostingFifoPolicy._ensure_source(posting)
        if not isinstance(candidates, tuple) or not isinstance(locations, tuple):
            raise InvalidStockPostingFifoPlanError(
                "Нужны tuple кандидатов и снимков локаций."
            )
        StockPostingPolicy.ensure_positions(
            entries=posting.entries, positions=positions
        )
        positions_by_id = {position.id: position for position in positions}
        locations_by_id = {}
        for location in locations:
            if not isinstance(location, StockLocationSnapshot):
                raise InvalidStockPostingFifoPlanError(
                    "Нужны специализированные снимки локаций."
                )
            location.ensure_valid()
            if location.id in locations_by_id:
                raise InvalidStockPostingFifoPlanError("Локации не должны повторяться.")
            locations_by_id[location.id] = location
        if set(locations_by_id) != {
            position.dimensions.location_id for position in positions
        }:
            raise InvalidStockPostingFifoPlanError(
                "Нужны ровно используемые исходными позициями локации."
            )
        groups = {position.id: [] for position in positions}
        identifiers = set()
        sources = set()
        for candidate in candidates:
            if not isinstance(candidate, ValuationLayerFifoSnapshot):
                raise InvalidStockPostingFifoPlanError(
                    "Нужны специализированные кандидаты FIFO."
                )
            candidate.ensure_valid()
            source = (
                candidate.layer.source.posting_id,
                candidate.layer.source.ledger_entry_id,
            )
            if candidate.layer.id in identifiers or source in sources:
                raise InvalidStockPostingFifoPlanError(
                    "Слои и источники поступления уникальны во всём пуле проведения."
                )
            if candidate.layer.source.position_id not in groups:
                raise InvalidStockPostingFifoPlanError(
                    "Кандидат относится к позиции вне этого ISSUE."
                )
            identifiers.add(candidate.layer.id)
            sources.add(source)
            groups[candidate.layer.source.position_id].append(candidate)
        plans = []
        for entry in posting.entries:
            position = positions_by_id[entry.position_id]
            issue = StockIssueValuationPolicy.build_snapshot(
                posting=posting,
                ledger_entry_id=entry.id,
                position=position,
                location=locations_by_id[position.dimensions.location_id],
            )
            plans.append(
                StockIssueFifoPlanSnapshot.create(
                    issue=issue, candidates=tuple(groups[entry.position_id])
                )
            )
        return tuple(plans)

    @staticmethod
    def ensure_plans(
        *, posting: StockPostingSnapshot, plans: tuple[StockIssueFifoPlanSnapshot, ...]
    ) -> None:
        """Проверяет полное упорядоченное покрытие исходного Ledger и глобальную уникальность кандидатов."""
        StockPostingFifoPolicy._ensure_source(posting)
        if not isinstance(plans, tuple) or len(plans) != len(posting.entries):
            raise InvalidStockPostingFifoPlanError(
                "Каждой записи Ledger нужен ровно один FIFO-план."
            )
        identifiers = set()
        sources = set()
        for entry, plan in zip(posting.entries, plans):
            if not isinstance(plan, StockIssueFifoPlanSnapshot):
                raise InvalidStockPostingFifoPlanError(
                    "Нужны специализированные FIFO-планы записей."
                )
            plan.ensure_valid()
            issue = plan.issue
            if (
                issue.posting_id,
                issue.ledger_entry_id,
                issue.position_id,
                issue.base_uom,
                issue.quantity.value,
                issue.issued_at,
            ) != (
                posting.id,
                entry.id,
                entry.position_id,
                entry.base_uom,
                entry.quantity_delta.value.copy_abs(),
                posting.posted_at,
            ):
                raise InvalidStockPostingFifoPlanError(
                    "Планы должны точно покрывать исходные записи в порядке Ledger."
                )
            for candidate in plan.candidates:
                source = (
                    candidate.layer.source.posting_id,
                    candidate.layer.source.ledger_entry_id,
                )
                if candidate.layer.id in identifiers or source in sources:
                    raise InvalidStockPostingFifoPlanError(
                        "Слой либо источник поступления повторяется между планами проведения."
                    )
                identifiers.add(candidate.layer.id)
                sources.add(source)
