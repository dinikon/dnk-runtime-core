import json
from dataclasses import asdict
from pydantic import TypeAdapter
from src.modules.inventory.application.stock_document.command.post_return.dto import (
    PostReturnResultDTO,
)


class ReturnPostingRecordMapper:
    """Кодирует конкретный неизменяемый результат и типизированно читает доверенный JSON."""

    @staticmethod
    def to_record(result: PostReturnResultDTO) -> dict[str, object]:
        """Сохраняет Decimal строками без округления и без HTTP-схем."""
        return json.loads(json.dumps(asdict(result), default=str))

    @staticmethod
    def to_command(record: dict[str, object]) -> PostReturnResultDTO:
        """Восстанавливает только DTO собственного сценария с UUID, Decimal и временем."""
        return TypeAdapter(PostReturnResultDTO).validate_python(record)
