import json
from dataclasses import asdict
from pydantic import TypeAdapter
from src.modules.inventory.application.stock_document.command.create_status_change_draft.dto import (
    CreateStatusChangeDraftResultDTO,
)


class StatusChangeCreationResultMapper:
    """Кодирует конкретный неизменяемый результат и типизированно читает доверенный JSON."""

    @staticmethod
    def to_record(result: CreateStatusChangeDraftResultDTO) -> dict[str, object]:
        """Сохраняет Decimal строками без округления и без HTTP-схем."""
        return json.loads(json.dumps(asdict(result), default=str))

    @staticmethod
    def from_record(record: dict[str, object]) -> CreateStatusChangeDraftResultDTO:
        """Восстанавливает только DTO собственного сценария с UUID, Decimal и временем."""
        return TypeAdapter(CreateStatusChangeDraftResultDTO).validate_python(record)
