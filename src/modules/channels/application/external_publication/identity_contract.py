from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PublicationIdentityPolicyDTO:
    """Задаёт правила ключа обмена плагина без SQL и зависимости от транспорта."""

    key_path: tuple[str, ...]
    label: str
    help_title: str
    help_steps: tuple[str, ...]
    help_url: str
    recovery_verified: bool = False


@dataclass(frozen=True, slots=True)
class PublicationIdentityDiagnosticDTO:
    """Передаёт состояние ключа среди локально известных публикаций подключения."""

    state: str
    key: str | None
    conflict_count: int
