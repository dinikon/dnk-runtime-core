from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from src.modules.communication.application.delivery import HandleProviderWebhookUseCase
from src.modules.communication.application.message_template import (
    ActivateTemplateVersionUseCase,
    CreateTemplateVersionUseCase,
    CreateMessageTemplateUseCase,
    ListMessageTemplatesUseCase,
)
from src.modules.communication.application.outbound_message import (
    GetOutboundMessageUseCase,
    ListOutboundMessagesUseCase,
    ProcessOutboundMessageUseCase,
    SendCommunicationUseCase,
)
from src.modules.communication.application.provider_connection import (
    CreateProviderConnectionUseCase,
    CreateProviderConnectionUseCaseProtocol,
    ListProviderConnectionsUseCase,
    ListProviderConnectionsUseCaseProtocol,
)
from src.modules.communication.application.provider_connector import (
    ListProviderConnectorsUseCase,
    ListProviderConnectorsUseCaseProtocol,
    RegisterProviderConnectorUseCase,
    RegisterProviderConnectorUseCaseProtocol,
)
from src.modules.communication.domain.message_template import MessageTemplateService
from src.modules.communication.domain.delivery import DeliveryService
from src.modules.communication.domain.outbound_message import OutboundMessageService
from src.modules.communication.domain.provider_connection import (
    ProviderConnectionService,
)
from src.modules.communication.domain.provider_connector import ProviderConnectorService
from src.modules.communication.infrastructure.delivery import (
    OutboundProcessingRuntimeRepository,
)
from src.modules.communication.presentation.depends.infrastructure import (
    DeliveryRuntimeRepositoryDep,
    JsonPathServiceDep,
    JsonSchemaValidationServiceDep,
    MessageTemplateQueryRuntimeRepositoryDep,
    MessageTemplateRuntimeRepositoryDep,
    OutboundMessageRuntimeRepositoryDep,
    OutboundMessagePublisherDep,
    ProviderConnectionRuntimeRepositoryDep,
    ProviderConnectorRuntimeRepositoryDep,
    ProviderSenderRegistryDep,
    ProviderStatusMappingServiceDep,
    ProviderYamlLoaderDep,
    SecretCodecDep,
    TemplateRenderServiceDep,
    get_outbound_message_publisher,
    get_provider_sender_registry,
    get_runtime_command_gateway,
    get_runtime_field_type_policy,
    get_runtime_query_gateway,
)
from src.modules.shared.depends.clock import ClockDep


def get_provider_connector_service(
    repository: ProviderConnectorRuntimeRepositoryDep,
    clock: ClockDep,
) -> ProviderConnectorService:
    """Создает domain service provider connector aggregate."""
    return ProviderConnectorService(repository=repository, clock=clock)


ProviderConnectorServiceDep = Annotated[
    ProviderConnectorService,
    Depends(get_provider_connector_service),
]


def get_register_provider_connector_use_case(
    service: ProviderConnectorServiceDep,
    loader: ProviderYamlLoaderDep,
) -> RegisterProviderConnectorUseCaseProtocol:
    """Создает use case регистрации provider connector."""
    return RegisterProviderConnectorUseCase(service, loader)


RegisterProviderConnectorUseCaseDep = Annotated[
    RegisterProviderConnectorUseCaseProtocol,
    Depends(get_register_provider_connector_use_case),
]


def get_list_provider_connectors_use_case(
    repository: ProviderConnectorRuntimeRepositoryDep,
) -> ListProviderConnectorsUseCaseProtocol:
    """Создает use case списка provider connectors."""
    return ListProviderConnectorsUseCase(repository)


ListProviderConnectorsUseCaseDep = Annotated[
    ListProviderConnectorsUseCaseProtocol,
    Depends(get_list_provider_connectors_use_case),
]


def get_provider_connection_service(
    repository: ProviderConnectionRuntimeRepositoryDep,
    schema_validator: JsonSchemaValidationServiceDep,
    clock: ClockDep,
) -> ProviderConnectionService:
    return ProviderConnectionService(
        command_repository=repository,
        provider_lookup=repository,
        schema_validator=schema_validator,
        clock=clock,
    )


ProviderConnectionServiceDep = Annotated[
    ProviderConnectionService,
    Depends(get_provider_connection_service),
]


def get_create_provider_connection_use_case(
    service: ProviderConnectionServiceDep,
    secret_codec: SecretCodecDep,
) -> CreateProviderConnectionUseCaseProtocol:
    return CreateProviderConnectionUseCase(service, secret_codec)


CreateProviderConnectionUseCaseDep = Annotated[
    CreateProviderConnectionUseCaseProtocol,
    Depends(get_create_provider_connection_use_case),
]


def get_list_provider_connections_use_case(
    repository: ProviderConnectionRuntimeRepositoryDep,
) -> ListProviderConnectionsUseCaseProtocol:
    return ListProviderConnectionsUseCase(repository)


ListProviderConnectionsUseCaseDep = Annotated[
    ListProviderConnectionsUseCaseProtocol,
    Depends(get_list_provider_connections_use_case),
]


def get_message_template_service(
    repository: MessageTemplateRuntimeRepositoryDep,
    schema_validator: JsonSchemaValidationServiceDep,
    clock: ClockDep,
) -> MessageTemplateService:
    return MessageTemplateService(
        command_repository=repository,
        provider_lookup=repository,
        schema_validator=schema_validator,
        clock=clock,
    )


MessageTemplateServiceDep = Annotated[
    MessageTemplateService,
    Depends(get_message_template_service),
]


def get_create_message_template_use_case(
    service: MessageTemplateServiceDep,
) -> CreateMessageTemplateUseCase:
    return CreateMessageTemplateUseCase(service)


CreateMessageTemplateUseCaseDep = Annotated[
    CreateMessageTemplateUseCase,
    Depends(get_create_message_template_use_case),
]


def get_create_template_version_use_case(
    service: MessageTemplateServiceDep,
) -> CreateTemplateVersionUseCase:
    return CreateTemplateVersionUseCase(service)


CreateTemplateVersionUseCaseDep = Annotated[
    CreateTemplateVersionUseCase,
    Depends(get_create_template_version_use_case),
]


def get_activate_template_version_use_case(
    service: MessageTemplateServiceDep,
) -> ActivateTemplateVersionUseCase:
    return ActivateTemplateVersionUseCase(service)


ActivateTemplateVersionUseCaseDep = Annotated[
    ActivateTemplateVersionUseCase,
    Depends(get_activate_template_version_use_case),
]


def get_list_message_templates_use_case(
    repository: MessageTemplateQueryRuntimeRepositoryDep,
) -> ListMessageTemplatesUseCase:
    return ListMessageTemplatesUseCase(repository)


ListMessageTemplatesUseCaseDep = Annotated[
    ListMessageTemplatesUseCase,
    Depends(get_list_message_templates_use_case),
]


def get_outbound_message_service(
    repository: OutboundMessageRuntimeRepositoryDep,
    clock: ClockDep,
) -> OutboundMessageService:
    """Создает domain service outbound message aggregate."""
    return OutboundMessageService(repository=repository, clock=clock)


OutboundMessageServiceDep = Annotated[
    OutboundMessageService,
    Depends(get_outbound_message_service),
]


def get_delivery_service(
    repository: DeliveryRuntimeRepositoryDep,
    clock: ClockDep,
) -> DeliveryService:
    """Создает domain service delivery aggregate."""
    return DeliveryService(repository=repository, clock=clock)


DeliveryServiceDep = Annotated[
    DeliveryService,
    Depends(get_delivery_service),
]


def get_outbound_processing_repository(
    outbound_repository: OutboundMessageRuntimeRepositoryDep,
    delivery_service: DeliveryServiceDep,
) -> OutboundProcessingRuntimeRepository:
    """Создает processing adapter для outbound и delivery attempts."""
    return OutboundProcessingRuntimeRepository(
        outbound_repository=outbound_repository,
        delivery_service=delivery_service,
    )


OutboundProcessingRuntimeRepositoryDep = Annotated[
    OutboundProcessingRuntimeRepository,
    Depends(get_outbound_processing_repository),
]


def get_send_communication_use_case(
    repository: OutboundMessageRuntimeRepositoryDep,
    service: OutboundMessageServiceDep,
    provider_connection_lookup: ProviderConnectionRuntimeRepositoryDep,
    schema_validator: JsonSchemaValidationServiceDep,
) -> SendCommunicationUseCase:
    """Создает use case постановки outbound communication send."""
    return SendCommunicationUseCase(
        repository=repository,
        service=service,
        template_lookup=repository,
        schema_validator=schema_validator,
        provider_connection_lookup=provider_connection_lookup,
    )


SendCommunicationUseCaseDep = Annotated[
    SendCommunicationUseCase,
    Depends(get_send_communication_use_case),
]


def get_process_outbound_message_use_case(
    repository: OutboundProcessingRuntimeRepositoryDep,
    sender_registry: ProviderSenderRegistryDep,
    template_renderer: TemplateRenderServiceDep,
    clock: ClockDep,
) -> ProcessOutboundMessageUseCase:
    return ProcessOutboundMessageUseCase(
        repository=repository,
        sender_registry=sender_registry,
        template_renderer=template_renderer,
        clock=clock,
    )


ProcessOutboundMessageUseCaseDep = Annotated[
    ProcessOutboundMessageUseCase,
    Depends(get_process_outbound_message_use_case),
]


def get_handle_provider_webhook_use_case(
    repository: DeliveryRuntimeRepositoryDep,
    service: DeliveryServiceDep,
    json_path: JsonPathServiceDep,
    status_mapper: ProviderStatusMappingServiceDep,
) -> HandleProviderWebhookUseCase:
    return HandleProviderWebhookUseCase(
        repository=repository,
        service=service,
        json_path=json_path,
        status_mapper=status_mapper,
    )


HandleProviderWebhookUseCaseDep = Annotated[
    HandleProviderWebhookUseCase,
    Depends(get_handle_provider_webhook_use_case),
]


def get_get_outbound_message_use_case(
    repository: OutboundMessageRuntimeRepositoryDep,
) -> GetOutboundMessageUseCase:
    return GetOutboundMessageUseCase(repository)


GetOutboundMessageUseCaseDep = Annotated[
    GetOutboundMessageUseCase,
    Depends(get_get_outbound_message_use_case),
]


def get_list_outbound_messages_use_case(
    repository: OutboundMessageRuntimeRepositoryDep,
) -> ListOutboundMessagesUseCase:
    return ListOutboundMessagesUseCase(repository)


ListOutboundMessagesUseCaseDep = Annotated[
    ListOutboundMessagesUseCase,
    Depends(get_list_outbound_messages_use_case),
]


__all__ = [
    "ActivateTemplateVersionUseCaseDep",
    "CreateMessageTemplateUseCaseDep",
    "CreateProviderConnectionUseCaseDep",
    "CreateTemplateVersionUseCaseDep",
    "DeliveryRuntimeRepositoryDep",
    "DeliveryServiceDep",
    "GetOutboundMessageUseCaseDep",
    "HandleProviderWebhookUseCaseDep",
    "ListMessageTemplatesUseCaseDep",
    "ListOutboundMessagesUseCaseDep",
    "ListProviderConnectionsUseCaseDep",
    "ListProviderConnectorsUseCaseDep",
    "MessageTemplateServiceDep",
    "OutboundMessageRuntimeRepositoryDep",
    "OutboundMessageServiceDep",
    "OutboundMessagePublisherDep",
    "OutboundProcessingRuntimeRepositoryDep",
    "ProcessOutboundMessageUseCaseDep",
    "ProviderConnectionServiceDep",
    "ProviderConnectorServiceDep",
    "ProviderSenderRegistryDep",
    "RegisterProviderConnectorUseCaseDep",
    "SendCommunicationUseCaseDep",
    "get_delivery_service",
    "get_message_template_service",
    "get_outbound_processing_repository",
    "get_outbound_message_publisher",
    "get_provider_sender_registry",
    "get_runtime_command_gateway",
    "get_runtime_field_type_policy",
    "get_runtime_query_gateway",
]
