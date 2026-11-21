from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CreateWarehouseCommand:
    """Передаёт пользовательские код и название нового склада."""

    code: str
    name: str
