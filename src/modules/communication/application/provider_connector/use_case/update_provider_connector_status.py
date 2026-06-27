from typing import Protocol

from src.modules.communication.application.provider_connector.command import (
    UpdateProviderConnectorStatusCommand,
)
from src.modules.communication.application.provider_connector.dto import (
    ProviderConnectorDTO,
)
from src.modules.communication.domain.provider_connector import (
    ConnectorStatus,
    ProviderConnector,
    ProviderConnectorService,
)


class UpdateProviderConnectorStatusUseCaseProtocol(Protocol):
    """Порт use case смены статуса provider connector."""

    async def __call__(
        self,
        command: UpdateProviderConnectorStatusCommand,
    ) -> ProviderConnectorDTO:
        """Меняет статус provider connector и возвращает DTO."""
        ...


class UpdateProviderConnectorStatusUseCase:
    """Use case смены статуса provider connector."""

    def __init__(self, service: ProviderConnectorService) -> None:
        """Инициализирует use case доменным service."""
        self._service = service

    async def __call__(
        self,
        command: UpdateProviderConnectorStatusCommand,
    ) -> ProviderConnectorDTO:
        """Выполняет смену статуса provider connector."""
        connector = await self._service.change_connector_status(
            tenant_id=command.tenant_id,
            provider_connector_id=command.provider_connector_id,
            status=ConnectorStatus(command.status),
        )
        return self._to_dto(connector)

    @staticmethod
    def _to_dto(connector: ProviderConnector) -> ProviderConnectorDTO:
        """Мапит ProviderConnector в ProviderConnectorDTO."""
        connector_spec = connector.yaml_spec or {}
        return ProviderConnectorDTO(
            provider_connector_id=connector.provider_connector_id.uuid,
            provider_code=connector.provider_code,
            provider_name=connector.provider_name,
            version=connector.version,
            connector_type=connector.connector_type,
            channels=list(connector_spec.get("channels") or []),
            config_schema=dict(connector_spec.get("config_schema") or {}),
            secrets_schema=dict(connector_spec.get("secrets_schema") or {}),
            status=connector.status,
            created_at=connector.created_at,
            updated_at=connector.updated_at,
        )


__all__ = [
    "UpdateProviderConnectorStatusUseCase",
    "UpdateProviderConnectorStatusUseCaseProtocol",
]
