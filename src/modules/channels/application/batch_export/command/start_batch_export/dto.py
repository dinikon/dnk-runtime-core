from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class StartBatchExportResultDTO:
    """Возвращает принятую, в том числе уже активную, операцию."""

    run_id: UUID
