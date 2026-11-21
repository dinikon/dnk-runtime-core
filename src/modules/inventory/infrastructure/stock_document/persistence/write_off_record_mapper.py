import json
from dataclasses import asdict
from pydantic import TypeAdapter
from src.modules.inventory.application.stock_document.command.post_write_off.dto import (
    PostWriteOffResultDTO,
)


class WriteOffPostingRecordMapper:
    """Кодирует конкретный неизменяемый результат и типизированно читает доверенный JSON."""

    @staticmethod
    def to_record(result: PostWriteOffResultDTO) -> dict[str, object]:
        """Сохраняет Decimal строками без округления и без HTTP-схем."""
        return json.loads(json.dumps(asdict(result), default=str))

    @staticmethod
    def to_command(record: dict[str, object]) -> PostWriteOffResultDTO:
        """Восстанавливает только DTO собственного сценария с UUID, Decimal и временем."""
        return TypeAdapter(PostWriteOffResultDTO).validate_python(record)
