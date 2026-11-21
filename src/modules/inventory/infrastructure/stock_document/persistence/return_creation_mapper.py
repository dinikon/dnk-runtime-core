import json
from dataclasses import asdict
from pydantic import TypeAdapter
from src.modules.inventory.application.stock_document.command.create_return_draft.dto import (
    CreateReturnDraftResultDTO,
)


class ReturnCreationResultMapper:
    """Кодирует конкретный неизменяемый результат и типизированно читает доверенный JSON."""

    @staticmethod
    def to_record(result: CreateReturnDraftResultDTO) -> dict[str, object]:
        """Сохраняет Decimal строками без округления и без HTTP-схем."""
        return json.loads(json.dumps(asdict(result), default=str))

    @staticmethod
    def from_record(record: dict[str, object]) -> CreateReturnDraftResultDTO:
        """Восстанавливает только DTO собственного сценария с UUID, Decimal и временем."""
        return TypeAdapter(CreateReturnDraftResultDTO).validate_python(record)
