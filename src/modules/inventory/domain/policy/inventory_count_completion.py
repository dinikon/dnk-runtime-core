from datetime import datetime

from src.modules.inventory.domain.inventory_count.adjustment_source_snapshot import (
    InventoryCountAdjustmentSourceSnapshot,
)
from src.modules.inventory.domain.inventory_count.error import (
    InventoryCountCompletionError,
)
from src.modules.inventory.domain.inventory_count.result_snapshot import (
    InventoryCountResultSnapshot,
)
from src.modules.inventory.domain.inventory_count.time import (
    normalize_inventory_count_time,
)
from src.modules.inventory.domain.inventory_count.value_object.completion import (
    InventoryCountCompletionVO,
)
from src.modules.inventory.domain.inventory_count.value_object.result_ref import (
    InventoryCountResultRefVO,
)
from src.modules.inventory.domain.inventory_count.value_object.status import (
    InventoryCountStatus,
)
from src.modules.inventory.domain.policy.inventory_count_adjustment_document import (
    InventoryCountAdjustmentDocumentPolicy,
)
from src.modules.inventory.domain.policy.stock_adjustment_application import (
    StockAdjustmentApplicationPolicy,
)
from src.modules.inventory.domain.stock_document.adjustment_completion_snapshot import (
    StockDocumentAdjustmentCompletionSnapshot,
)
from src.modules.inventory.domain.stock_document.value_object.adjustment_line import (
    StockAdjustmentLineVO,
)
from src.modules.inventory.domain.stock_document.value_object.document_source import (
    DocumentSourceVO,
)
from src.modules.inventory.domain.stock_execution.adjustment_snapshot import (
    StockAdjustmentExecutionSnapshot,
)
from src.modules.inventory.domain.stock_posting.adjustment_application_snapshot import (
    StockAdjustmentApplicationSnapshot,
)
from src.modules.inventory.domain.stock_posting.snapshot import StockPostingSnapshot


class InventoryCountCompletionPolicy:
    """Завершает зарегистрированный исторический результат по согласованным фактам без чтения живых остатков."""

    @staticmethod
    def ensure_result(
        *,
        inventory_count: InventoryCountAdjustmentSourceSnapshot,
        result: InventoryCountResultSnapshot,
        completed_at: datetime,
    ) -> datetime:
        """Требует текущий COUNTED и точно зарегистрированные результат, область и историческую версию."""
        if not isinstance(
            inventory_count, InventoryCountAdjustmentSourceSnapshot
        ) or not isinstance(result, InventoryCountResultSnapshot):
            raise InventoryCountCompletionError(
                "Нужны текущий снимок инвентаризации и её зарегистрированный результат."
            )
        inventory_count.ensure_valid()
        result.ensure_valid()
        normalized = normalize_inventory_count_time(completed_at)
        if (
            inventory_count.status is not InventoryCountStatus.COUNTED
            or inventory_count.result
            != InventoryCountResultRefVO(result.id, result.prepared_at)
            or inventory_count.baseline != result.baseline
            or inventory_count.id != result.inventory_count_id
            or inventory_count.warehouse_id != result.warehouse_id
            or inventory_count.owner_id != result.owner_id
            or inventory_count.scope != result.scope
            or result.inventory_count_version >= inventory_count.version
            or result.prepared_at > inventory_count.updated_at
            or normalized < inventory_count.updated_at
        ):
            raise InventoryCountCompletionError(
                "Результат, его ссылки, область, версия или время не соответствуют текущей COUNTED-инвентаризации."
            )
        return normalized

    @staticmethod
    def without_adjustment(
        *,
        inventory_count: InventoryCountAdjustmentSourceSnapshot,
        result: InventoryCountResultSnapshot,
        completed_at: datetime,
    ) -> InventoryCountCompletionVO:
        """Разрешает закрыть пустой или полностью совпавший результат без создания складских фактов."""
        normalized = InventoryCountCompletionPolicy.ensure_result(
            inventory_count=inventory_count, result=result, completed_at=completed_at
        )
        if any(not row.discrepancy.value.is_zero() for row in result.lines):
            raise InventoryCountCompletionError(
                "Ненулевые расхождения требуют полного применения корректировки."
            )
        return InventoryCountCompletionVO(normalized, None, None, None, None)

    @staticmethod
    def with_adjustment(
        *,
        inventory_count: InventoryCountAdjustmentSourceSnapshot,
        result: InventoryCountResultSnapshot,
        document: StockDocumentAdjustmentCompletionSnapshot,
        execution: StockAdjustmentExecutionSnapshot,
        posting: StockPostingSnapshot,
        application: StockAdjustmentApplicationSnapshot,
        completed_at: datetime,
    ) -> InventoryCountCompletionVO:
        """Сверяет все ненулевые наблюдения, полное исполнение, Ledger и сохранённые результаты применения."""
        normalized = InventoryCountCompletionPolicy.ensure_result(
            inventory_count=inventory_count, result=result, completed_at=completed_at
        )
        if not isinstance(
            document, StockDocumentAdjustmentCompletionSnapshot
        ) or not isinstance(execution, StockAdjustmentExecutionSnapshot):
            raise InventoryCountCompletionError(
                "Нужны завершённый документ и полный факт корректировки."
            )
        document.ensure_valid()
        execution.ensure_valid()
        if (
            document.source
            != DocumentSourceVO(
                InventoryCountAdjustmentDocumentPolicy.SOURCE_SYSTEM,
                str(result.id.uuid),
            )
            or document.warehouse_id != inventory_count.warehouse_id
            or document.owner_id != inventory_count.owner_id
            or execution.document_id != document.id
            or document.version != execution.document_version + 1
            or execution.warehouse_id != document.warehouse_id
            or execution.owner_id != document.owner_id
            or execution.executed_at < inventory_count.updated_at
            or document.updated_at < execution.executed_at
            or normalized < document.updated_at
        ):
            raise InventoryCountCompletionError(
                "Документ и факт не соответствуют результату, области, последовательности версий или времени."
            )
        observations = {
            (row.sheet_id, row.observation.id): row.observation
            for row in result.lines
            if not row.discrepancy.value.is_zero()
        }
        if not observations:
            raise InventoryCountCompletionError(
                "Нулевой результат завершается без корректировки."
            )
        lines = {}
        sources = set()
        for row in document.lines:
            line = row.as_line()
            binding = InventoryCountAdjustmentDocumentPolicy.line_binding(line)
            key = (binding.sheet_id, binding.count_line_id)
            observation = observations.get(key)
            if observation is None:
                raise InventoryCountCompletionError(
                    "Документ содержит лишнее или нулевое наблюдение."
                )
            expected = StockAdjustmentLineVO(
                observation.dimensions,
                observation.position_id,
                observation.position_version,
                observation.expected_qty,
                observation.counted_qty,
            )
            if line.adjustment != expected or line.base_uom != observation.base_uom:
                raise InventoryCountCompletionError(
                    "Измерения, цель, знак, единица или исходная позиция документа изменены."
                )
            sources.add(key)
            lines[line.id] = line
        if sources != set(observations) or set(lines) != {
            row.document_line_id for row in execution.lines
        }:
            raise InventoryCountCompletionError(
                "Все ненулевые строки результата должны быть исполнены ровно один раз."
            )
        for row in execution.lines:
            line = lines[row.document_line_id]
            if row.route.adjustment != line.adjustment or row.base_uom != line.base_uom:
                raise InventoryCountCompletionError(
                    "Факт не совпадает с точным переходом и единицей строки документа."
                )
        StockAdjustmentApplicationPolicy.ensure_compatible(
            application=application, posting=posting, execution=execution
        )
        if normalized < application.applied_at:
            raise InventoryCountCompletionError(
                "Завершение не может предшествовать применению Ledger."
            )
        return InventoryCountCompletionVO(
            normalized, document.id, document.version, execution.id, posting.id
        )
