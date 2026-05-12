from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from src.modules.communication.application.use_cases import (
    ActivateTemplateVersionUseCase,
    CreateMessageTemplateUseCase,
    CreateProviderConnectionUseCase,
    CreateTemplateVersionUseCase,
    GetOutboundMessageUseCase,
    HandleProviderWebhookUseCase,
    ListMessageTemplatesUseCase,
    ListOutboundMessagesUseCase,
    ListProviderConnectionsUseCase,
    ListProviderConnectorsUseCase,
    ProcessOutboundMessageUseCase,
    RegisterProviderConnectorUseCase,
    SendCommunicationUseCase,
)
from src.modules.communication.presentation.depends.infrastructure import (
    CommunicationRepositoryDep,
    JsonPathServiceDep,
    JsonSchemaValidationServiceDep,
    OutboundMessagePublisherDep,
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


def get_create_provider_connection_use_case(
    repository: CommunicationRepositoryDep,
    schema_validator: JsonSchemaValidationServiceDep,
    secret_codec: SecretCodecDep,
) -> CreateProviderConnectionUseCase:
    return CreateProviderConnectionUseCase(repository, schema_validator, secret_codec)


CreateProviderConnectionUseCaseDep = Annotated[
    CreateProviderConnectionUseCase,
    Depends(get_create_provider_connection_use_case),
]


def get_list_provider_connections_use_case(
    repository: CommunicationRepositoryDep,
) -> ListProviderConnectionsUseCase:
    return ListProviderConnectionsUseCase(repository)


ListProviderConnectionsUseCaseDep = Annotated[
    ListProviderConnectionsUseCase,
    Depends(get_list_provider_connections_use_case),
]


def get_create_message_template_use_case(
    repository: CommunicationRepositoryDep,
) -> CreateMessageTemplateUseCase:
    return CreateMessageTemplateUseCase(repository)


CreateMessageTemplateUseCaseDep = Annotated[
    CreateMessageTemplateUseCase,
    Depends(get_create_message_template_use_case),
]


def get_create_template_version_use_case(
    repository: CommunicationRepositoryDep,
    schema_validator: JsonSchemaValidationServiceDep,
) -> CreateTemplateVersionUseCase:
    return CreateTemplateVersionUseCase(repository, schema_validator)


CreateTemplateVersionUseCaseDep = Annotated[
    CreateTemplateVersionUseCase,
    Depends(get_create_template_version_use_case),
]


def get_activate_template_version_use_case(
    repository: CommunicationRepositoryDep,
    clock: ClockDep,
) -> ActivateTemplateVersionUseCase:
    return ActivateTemplateVersionUseCase(repository, clock)


ActivateTemplateVersionUseCaseDep = Annotated[
    ActivateTemplateVersionUseCase,
    Depends(get_activate_template_version_use_case),
]


def get_list_message_templates_use_case(
    repository: CommunicationRepositoryDep,
) -> ListMessageTemplatesUseCase:
    return ListMessageTemplatesUseCase(repository)


ListMessageTemplatesUseCaseDep = Annotated[
    ListMessageTemplatesUseCase,
    Depends(get_list_message_templates_use_case),
]


def get_send_communication_use_case(
    repository: CommunicationRepositoryDep,
    schema_validator: JsonSchemaValidationServiceDep,
    clock: ClockDep,
) -> SendCommunicationUseCase:
    return SendCommunicationUseCase(repository, schema_validator, clock)


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
    "OutboundMessagePublisherDep",
    "ProcessOutboundMessageUseCaseDep",
    "ProviderSenderRegistryDep",
    "RegisterProviderConnectorUseCaseDep",
    "SendCommunicationUseCaseDep",
    "get_communication_repository",
    "get_outbound_message_publisher",
    "get_provider_sender_registry",
    "get_runtime_field_type_policy",
    "get_runtime_gateway",
]
