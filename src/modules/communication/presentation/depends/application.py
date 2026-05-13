from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from src.modules.communication.application.use_cases import (
    ActivateTemplateVersionUseCase,
    CreateMessageTemplateUseCase,
    CreateProviderConnectionUseCase,
    CreateProviderConnectionUseCaseProtocol,
    CreateTemplateVersionUseCase,
    GetOutboundMessageUseCase,
    HandleProviderWebhookUseCase,
    ListMessageTemplatesUseCase,
    ListOutboundMessagesUseCase,
    ListProviderConnectionsUseCase,
    ListProviderConnectionsUseCaseProtocol,
    ListProviderConnectorsUseCase,
    ProcessOutboundMessageUseCase,
    RegisterProviderConnectorUseCase,
    SendCommunicationUseCase,
)
from src.modules.communication.domain.message_template import MessageTemplateService
from src.modules.communication.domain.provider_connection import (
    ProviderConnectionService,
)
from src.modules.communication.presentation.depends.infrastructure import (
    CommunicationRepositoryDep,
    JsonPathServiceDep,
    JsonSchemaValidationServiceDep,
    MessageTemplateQueryRuntimeRepositoryDep,
    MessageTemplateRuntimeRepositoryDep,
    OutboundMessagePublisherDep,
    ProviderConnectionRuntimeRepositoryDep,
    ProviderSenderRegistryDep,
    ProviderStatusMappingServiceDep,
    ProviderYamlLoaderDep,
    SecretCodecDep,
    TemplateRenderServiceDep,
    get_communication_repository,
    get_outbound_message_publisher,
    get_provider_sender_registry,
    get_runtime_field_type_policy,
    get_runtime_gateway,
)
from src.modules.shared.depends.clock import ClockDep


def get_register_provider_connector_use_case(
    repository: CommunicationRepositoryDep,
    loader: ProviderYamlLoaderDep,
) -> RegisterProviderConnectorUseCase:
    return RegisterProviderConnectorUseCase(repository, loader)


RegisterProviderConnectorUseCaseDep = Annotated[
    RegisterProviderConnectorUseCase,
    Depends(get_register_provider_connector_use_case),
]


def get_list_provider_connectors_use_case(
    repository: CommunicationRepositoryDep,
) -> ListProviderConnectorsUseCase:
    return ListProviderConnectorsUseCase(repository)


ListProviderConnectorsUseCaseDep = Annotated[
    ListProviderConnectorsUseCase,
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


def get_send_communication_use_case(
    repository: CommunicationRepositoryDep,
    provider_connection_lookup: ProviderConnectionRuntimeRepositoryDep,
    schema_validator: JsonSchemaValidationServiceDep,
    clock: ClockDep,
) -> SendCommunicationUseCase:
    return SendCommunicationUseCase(
        repository,
        schema_validator,
        clock,
        provider_connection_lookup=provider_connection_lookup,
    )


SendCommunicationUseCaseDep = Annotated[
    SendCommunicationUseCase,
    Depends(get_send_communication_use_case),
]


def get_process_outbound_message_use_case(
    repository: CommunicationRepositoryDep,
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
    repository: CommunicationRepositoryDep,
    json_path: JsonPathServiceDep,
    status_mapper: ProviderStatusMappingServiceDep,
    clock: ClockDep,
) -> HandleProviderWebhookUseCase:
    return HandleProviderWebhookUseCase(repository, json_path, status_mapper, clock)


HandleProviderWebhookUseCaseDep = Annotated[
    HandleProviderWebhookUseCase,
    Depends(get_handle_provider_webhook_use_case),
]


def get_get_outbound_message_use_case(
    repository: CommunicationRepositoryDep,
) -> GetOutboundMessageUseCase:
    return GetOutboundMessageUseCase(repository)


GetOutboundMessageUseCaseDep = Annotated[
    GetOutboundMessageUseCase,
    Depends(get_get_outbound_message_use_case),
]


def get_list_outbound_messages_use_case(
    repository: CommunicationRepositoryDep,
) -> ListOutboundMessagesUseCase:
    return ListOutboundMessagesUseCase(repository)


ListOutboundMessagesUseCaseDep = Annotated[
    ListOutboundMessagesUseCase,
    Depends(get_list_outbound_messages_use_case),
]


__all__ = [
    "ActivateTemplateVersionUseCaseDep",
    "CommunicationRepositoryDep",
    "CreateMessageTemplateUseCaseDep",
    "CreateProviderConnectionUseCaseDep",
    "CreateTemplateVersionUseCaseDep",
    "GetOutboundMessageUseCaseDep",
    "HandleProviderWebhookUseCaseDep",
    "ListMessageTemplatesUseCaseDep",
    "ListOutboundMessagesUseCaseDep",
    "ListProviderConnectionsUseCaseDep",
    "ListProviderConnectorsUseCaseDep",
    "MessageTemplateServiceDep",
    "OutboundMessagePublisherDep",
    "ProcessOutboundMessageUseCaseDep",
    "ProviderConnectionServiceDep",
    "ProviderSenderRegistryDep",
    "RegisterProviderConnectorUseCaseDep",
    "SendCommunicationUseCaseDep",
    "get_communication_repository",
    "get_message_template_service",
    "get_outbound_message_publisher",
    "get_provider_sender_registry",
    "get_runtime_field_type_policy",
    "get_runtime_gateway",
]
