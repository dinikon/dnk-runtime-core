"""Снимок доступа для вызова API после завершения транзакции."""

from dataclasses import dataclass, field

from src.modules.channels.application.sync_run.port.source import PublicationCheckpoint
from src.modules.channels.domain.channel.value_object.connection_config import (
    ConnectionConfigVO,
)


@dataclass(frozen=True, slots=True)
class PrepareSyncStepResultDTO:
    """Не передаётся в HTTP, логи либо payload задания."""

    platform_kind: str
    config: ConnectionConfigVO
    encrypted_credentials: bytes = field(repr=False)
    revision: int
    checkpoint: PublicationCheckpoint
    parent_external_id: str | None
