from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class DiffSchemaResultDTO:
    """DTO со статистикой примененного diff-плана schema_registry."""

    tenant_id: UUID
    schema_name: str
    seed_path: str
    total_operations: int
    destructive_operations: int
    non_destructive_operations: int
    has_changes: bool
    has_destructive_changes: bool
