from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class GetReturnExecutionResultQuery:
    """Задаёт чтение первоначального результата конкретного исполнения возврата."""

    identifier: UUID
