import json
from dataclasses import fields
from src.modules.channels.domain.channel.value_object.identifier import ChannelIdVO
from src.modules.channels.domain.publication_import_run.value_object.identifier import (
    PublicationImportRunIdVO,
)
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from typing import Any, Mapping
from src.modules.channels.domain.publication_import_run.aggregate import (
    PublicationImportRun,
)


class PublicationImportRunMapper:
    """Переводит запуск в SQL-представление и обратно без I/O."""

    @staticmethod
    def to_values(run: PublicationImportRun) -> dict[str, Any]:
        """Извлекает состояние и сериализует непрозрачный курсор."""
        values = {field.name: getattr(run, field.name) for field in fields(run)}
        for key in ("id", "channel_id", "job_id"):
            values[key] = values[key].uuid
        values["checkpoint"] = json.loads(run.checkpoint)
        return values

    @staticmethod
    def to_domain(row: Mapping[str, Any]) -> PublicationImportRun:
        """Восстанавливает запуск через фабрику с проверкой инвариантов."""
        values = dict(row)
        values["id"] = PublicationImportRunIdVO.from_value(values["id"])
        values["channel_id"] = ChannelIdVO.from_value(values["channel_id"])
        values["job_id"] = EntityIdVO.from_value(values["job_id"])
        values["checkpoint"] = json.dumps(values["checkpoint"], sort_keys=True)
        return PublicationImportRun.restore(**values)
