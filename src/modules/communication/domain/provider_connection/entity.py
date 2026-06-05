from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Self

from src.modules.communication.domain.provider_connection.value_object import (
    ProviderConnectionCodeVO,
    ProviderConnectionIdVO,
    ProviderConnectionNameVO,
    ProviderConnectionStatusVO,
)
from src.modules.communication.domain.provider_connection.error import (
    ProviderConnectionDeleteForbiddenError,
    ProviderConnectionInactiveError,
    ProviderConnectionStatusTransitionError,
)
from src.modules.communication.domain.provider_connector.value_object import (
    ProviderConnectorIdVO,
)
from src.modules.shared import EntityIdVO


@dataclass(slots=True)
class ProviderConnectionEntity:
    """Доменная сущность подключения provider connector к tenant."""

    provider_connection_id: ProviderConnectionIdVO
    created_at: datetime
    updated_at: datetime
    tenant_id: EntityIdVO

    provider_connector_id: ProviderConnectorIdVO
    connection_code: ProviderConnectionCodeVO
    connection_name: ProviderConnectionNameVO
    channel_code: str
    config: dict[str, Any]
    secret_ref: str | None
    secrets_b64: str | None
    status: ProviderConnectionStatusVO

    @classmethod
    def create(
        cls,
        *,
        provider_connection_id: ProviderConnectionIdVO,
        tenant_id: EntityIdVO,
        provider_connector_id: ProviderConnectorIdVO,
        connection_code: str,
        connection_name: str,
        channel_code: str,
        config: dict[str, Any],
        secret_ref: str | None,
        secrets_b64: str | None,
        now: datetime,
        status: ProviderConnectionStatusVO | str = ProviderConnectionStatusVO.ACTIVE,
    ) -> Self:
        """Создает active provider connection с едиными created_at/updated_at."""
        return cls(
            provider_connection_id=provider_connection_id,
            created_at=now,
            updated_at=now,
            tenant_id=tenant_id,
            provider_connector_id=provider_connector_id,
            connection_code=ProviderConnectionCodeVO(connection_code),
            connection_name=ProviderConnectionNameVO(connection_name),
            channel_code=channel_code,
            config=dict(config),
            secret_ref=secret_ref,
            secrets_b64=secrets_b64,
            status=ProviderConnectionStatusVO(status),
        )

    def change_status(
        self,
        *,
        status: ProviderConnectionStatusVO,
        now: datetime,
    ) -> Self:
        """Меняет статус connection в рамках разрешенного lifecycle."""
        target_status = ProviderConnectionStatusVO(status)
        if self.status == ProviderConnectionStatusVO.ARCHIVED:
            raise ProviderConnectionStatusTransitionError()
        if target_status == ProviderConnectionStatusVO.ARCHIVED:
            raise ProviderConnectionStatusTransitionError()
        if target_status == self.status:
            return self

        allowed = {
            ProviderConnectionStatusVO.ACTIVE,
            ProviderConnectionStatusVO.DISABLED,
        }
        if self.status not in allowed or target_status not in allowed:
            raise ProviderConnectionStatusTransitionError()

        self.status = target_status
        self.updated_at = now
        return self

    def ensure_deletable(self) -> None:
        """Проверяет, что connection можно удалить или архивировать."""
        if self.status != ProviderConnectionStatusVO.DISABLED:
            raise ProviderConnectionDeleteForbiddenError()

    def ensure_active(self) -> None:
        """Проверяет, что connection можно использовать для отправки."""
        if self.status != ProviderConnectionStatusVO.ACTIVE:
            raise ProviderConnectionInactiveError()

    def archive(self, *, now: datetime) -> Self:
        """Переводит disabled connection в невосстанавливаемый archived статус."""
        self.ensure_deletable()
        self.status = ProviderConnectionStatusVO.ARCHIVED
        self.updated_at = now
        return self


__all__ = [
    "ProviderConnectionEntity",
]
