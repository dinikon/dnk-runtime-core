from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class GetInternalMoveExecutionResultQuery:
    """Задаёт чтение первоначального результата конкретного исполнения перемещения."""

    identifier: UUID
