from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ResolveReadableTenantByHostQuery:
    """Передаёт хост для проверки доступа к данным tenant."""

    host: str
