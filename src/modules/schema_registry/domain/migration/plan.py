from dataclasses import dataclass, field

from src.modules.schema_registry.domain.migration.operations import MigrationOperation


@dataclass(slots=True)
class MigrationPlan:
    operations: list[MigrationOperation,] = field(default_factory=list)
    destructive_operations: list[MigrationOperation,] = field(default_factory=list)

    def add(self, operation: MigrationOperation) -> None:
        self.operations.append(operation)

    def extend(self, operations: list[MigrationOperation]) -> None:
        self.operations.extend(operations)

    def add_destructive(self, operation: MigrationOperation) -> None:
        self.destructive_operations.append(operation)
        self.operations.append(operation)

    def extend_destructive(self, operations: list[MigrationOperation]) -> None:
        self.destructive_operations.extend(operations)
        self.operations.extend(operations)

    @property
    def is_empty(self) -> bool:
        return not self.operations

    @property
    def has_destructive_changes(self) -> bool:
        return bool(self.destructive_operations)
