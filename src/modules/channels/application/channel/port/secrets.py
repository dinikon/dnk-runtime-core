from typing import Protocol
from uuid import UUID


class ConnectionSecretsProtocol(Protocol):
    """Защищает credentials с привязкой к tenant и Connection."""

    def seal(self, tenant_id: UUID, connection_id: UUID, values: dict[str, str]) -> str:
        """Возвращает ciphertext без логирования входа."""
        ...
