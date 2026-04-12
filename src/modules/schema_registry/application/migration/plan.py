from dataclasses import dataclass, field

from src.modules.schema_registry.application.migration.operations import (
    MigrationOperation,
)


@dataclass(slots=True)
class MigrationPlan:
    """Хранит упорядоченный набор migration-операций и destructive-подмножество."""

    operations: list[MigrationOperation] = field(default_factory=list)
    destructive_operations: list[MigrationOperation] = field(default_factory=list)

    def add(self, operation: MigrationOperation) -> None:
        """Добавляет безопасную или нейтральную операцию в общий список."""
        self.operations.append(operation)

    def extend(self, operations: list[MigrationOperation]) -> None:
        """Добавляет несколько операций в общий список."""
        self.operations.extend(operations)

    def add_destructive(self, operation: MigrationOperation) -> None:
        """Добавляет destructive-операцию и помечает ее в отдельном списке."""
        self.destructive_operations.append(operation)
        self.operations.append(operation)

    def extend_destructive(self, operations: list[MigrationOperation]) -> None:
        """Добавляет несколько destructive-операций с сохранением общего порядка."""
        self.destructive_operations.extend(operations)
        self.operations.extend(operations)

    @property
    def is_empty(self) -> bool:
        """Показывает, что план не содержит операций."""
        return not self.operations

    @property
    def has_destructive_changes(self) -> bool:
        """Показывает, содержит ли план destructive-операции."""
        return bool(self.destructive_operations)
