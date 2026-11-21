from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class GetWriteOffExecutionResultQuery:
    """Задаёт чтение первоначального результата конкретного исполнения списания."""

    identifier: UUID
