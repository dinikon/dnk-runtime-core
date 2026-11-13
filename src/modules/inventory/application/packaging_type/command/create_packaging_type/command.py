from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CreatePackagingTypeCommand:
    """Передаёт ручные код и название без настроек активности и хранения."""

    code: str
    name: str
