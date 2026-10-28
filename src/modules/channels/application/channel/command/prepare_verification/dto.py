from dataclasses import dataclass, field

from src.modules.channels.domain.channel.value_object.connection_config import (
    ConnectionConfigVO,
)


@dataclass(frozen=True, slots=True)
class PrepareVerificationDTO:
    """Снимок для API-вызова после завершения UoW."""

    platform_kind: str
    config: ConnectionConfigVO
    encrypted_credentials: bytes = field(repr=False)
