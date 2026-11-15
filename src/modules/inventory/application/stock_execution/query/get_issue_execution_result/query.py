from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class GetIssueExecutionResultQuery:
    """Задаёт чтение первоначального результата конкретного исполнения расхода."""

    identifier: UUID
