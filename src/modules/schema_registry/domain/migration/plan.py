from dataclasses import dataclass, field

from src.modules.schema_registry.domain.migration.operations import MigrationOperation


@dataclass(slots=True)
class MigrationPlan:
    operations: list[MigrationOperation,] = field(default_factory=list)

    def add(self, operation: MigrationOperation) -> None:
        self.operations.append(operation)

    def extend(self, operations: list[MigrationOperation]) -> None:
        self.operations.extend(operations)

    @property
    def is_empty(self) -> bool:
        return not self.operations
