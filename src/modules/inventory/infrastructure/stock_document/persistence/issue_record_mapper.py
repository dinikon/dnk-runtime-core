import json
from dataclasses import asdict
from pydantic import TypeAdapter
from src.modules.inventory.application.stock_document.command.post_issue.dto import (
    PostIssueResultDTO,
)


class IssuePostingRecordMapper:
    """Кодирует конкретный неизменяемый результат и типизированно читает доверенный JSON."""

    @staticmethod
    def to_record(result: PostIssueResultDTO) -> dict[str, object]:
        """Сохраняет Decimal строками без округления и без HTTP-схем."""
        return json.loads(json.dumps(asdict(result), default=str))

    @staticmethod
    def to_command(record: dict[str, object]) -> PostIssueResultDTO:
        """Восстанавливает только DTO собственного сценария с UUID, Decimal и временем."""
        return TypeAdapter(PostIssueResultDTO).validate_python(record)
