from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class GetStatusChangeExecutionResultQuery:
    """Задаёт чтение первоначального результата конкретного исполнения изменения состояния."""

    identifier: UUID
