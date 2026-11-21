import json
from dataclasses import asdict
from pydantic import TypeAdapter
from src.modules.inventory.application.stock_document.command.create_write_off_draft.dto import (
    CreateWriteOffDraftResultDTO,
)


class WriteOffCreationResultMapper:
    """Кодирует конкретный неизменяемый результат и типизированно читает доверенный JSON."""

    @staticmethod
    def to_record(result: CreateWriteOffDraftResultDTO) -> dict[str, object]:
        """Сохраняет Decimal строками без округления и без HTTP-схем."""
        return json.loads(json.dumps(asdict(result), default=str))

    @staticmethod
    def from_record(record: dict[str, object]) -> CreateWriteOffDraftResultDTO:
        """Восстанавливает только DTO собственного сценария с UUID, Decimal и временем."""
        return TypeAdapter(CreateWriteOffDraftResultDTO).validate_python(record)
