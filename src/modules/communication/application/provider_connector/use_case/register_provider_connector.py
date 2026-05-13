from typing import Protocol

from src.modules.communication.application.provider_connector.command import (
    RegisterProviderConnectorCommand,
)
from src.modules.communication.application.provider_connector.dto import (
    ProviderConnectorDTO,
)
from src.modules.communication.application.services import ProviderYamlLoader
from src.modules.communication.domain.provider_connector import (
    ProviderConnector,
    ProviderConnectorService,
)


class RegisterProviderConnectorUseCaseProtocol(Protocol):
    """Порт use case регистрации provider connector."""

    async def __call__(
        self,
        command: RegisterProviderConnectorCommand,
    ) -> ProviderConnectorDTO:
        """Импортирует YAML provider connector и возвращает DTO."""
        ...


class RegisterProviderConnectorUseCase:
    """Use case регистрации provider connector через доменный сервис."""

    def __init__(
        self,
        service: ProviderConnectorService,
        loader: ProviderYamlLoader,
    ) -> None:
        """Инициализирует use case доменным сервисом и YAML loader-ом."""
        self._service = service
        self._loader = loader

    async def __call__(
        self,
        command: RegisterProviderConnectorCommand,
    ) -> ProviderConnectorDTO:
        """Парсит YAML, регистрирует connector и мапит entity в DTO."""
        parsed = self._loader.load(command.yaml_content)
        connector = await self._service.register_connector(
            tenant_id=command.tenant_id,
            provider_connector_id=command.provider_connector_id,
            spec=parsed.spec,
            checksum=parsed.checksum,
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
    "RegisterProviderConnectorUseCase",
    "RegisterProviderConnectorUseCaseProtocol",
]
