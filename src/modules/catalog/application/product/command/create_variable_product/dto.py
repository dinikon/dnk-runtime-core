from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class CreateVariableProductResultDTO:
    """Собственный результат сценария create_variable_product."""

    id: UUID
    revision: int
