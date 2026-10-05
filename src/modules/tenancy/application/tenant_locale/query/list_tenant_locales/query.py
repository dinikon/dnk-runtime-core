from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ListTenantLocalesQuery:
    """Запрос выбранных локалей текущего tenant."""
