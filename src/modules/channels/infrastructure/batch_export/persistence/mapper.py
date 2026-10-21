from collections.abc import Mapping
from dataclasses import asdict
from typing import Any
from src.modules.channels.domain.batch_export.aggregate import BatchExportRun
from src.modules.channels.domain.batch_export.value_object.item import ExportItemVO
from src.modules.channels.domain.content_update.value_object.texts import (
    ContentTextsVO,
    LocalizedTextVO,
)


class BatchExportMapper:
    """Преобразует собственные DTO и строки без I/O."""

    @staticmethod
    def run(row: Mapping[str, Any]) -> BatchExportRun:
        """Восстанавливает lifecycle только фабрикой Domain."""
        return BatchExportRun.restore(
            row["id"], **{k: v for k, v in row.items() if k != "id"}
        )

    @staticmethod
    def values(run: BatchExportRun) -> dict[str, Any]:
        """Извлекает поля корня без изменения состояния."""
        return asdict(run)

    @staticmethod
    def item(row: Mapping[str, Any]) -> ExportItemVO:
        """Восстанавливает типизированную цель из версии снимка."""
        values = {k: v for k, v in row.items() if k != "run_id"}
        values["issues"] = tuple(values["issues"])
        if values["desired"] is not None:
            values["desired"] = ContentTextsVO(
                tuple(LocalizedTextVO(**t) for t in values["desired"]["translations"])
            )
        return ExportItemVO(**values)

    @staticmethod
    def item_values(item: ExportItemVO) -> dict[str, Any]:
        """Сериализует JSON только принадлежащих позиции значений."""
        values = asdict(item)
        values["issues"] = list(item.issues)
        if item.desired is not None:
            values["desired"] = {
                "version": 1,
                "translations": [asdict(t) for t in item.desired.translations],
            }
        return values
