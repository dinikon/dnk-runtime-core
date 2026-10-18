from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from collections.abc import Mapping
from typing import Any
from dataclasses import fields
from src.modules.channels.domain.sync_run.aggregate import SyncRun


class SyncRunMapper:
    """Преобразует checkpoint и прогресс без бизнес-переходов и SQL."""

    @staticmethod
    def to_domain(row: Mapping[str, Any]) -> SyncRun:
        """Восстанавливает ранее сохранённый run."""
        values = dict(row)
        values["identifier"] = EntityIdVO(values.pop("id"))
        values.pop("operation")
        for name in ("limitations", "request_keys"):
            values[name] = tuple(values[name])
        if values["channel_id"] is not None:
            values["channel_id"] = EntityIdVO(values["channel_id"])
        if values["connection_id"] is not None:
            values["connection_id"] = EntityIdVO(values["connection_id"])
        if values["actor_id"] is not None:
            values["actor_id"] = EntityIdVO(values["actor_id"])
        if values["job_id"] is not None:
            values["job_id"] = EntityIdVO(values["job_id"])
        return SyncRun.restore(**values)

    @staticmethod
    def to_values(run: SyncRun) -> dict[str, Any]:
        """Извлекает значения для записи без изменения статуса."""
        values = {
            item.name: (
                getattr(run, item.name).uuid
                if isinstance(getattr(run, item.name), EntityIdVO)
                else getattr(run, item.name)
            )
            for item in fields(run)
        }
        values["operation"] = "initialize_publications"
        for name in ("limitations", "request_keys"):
            values[name] = list(values[name])
        return values
