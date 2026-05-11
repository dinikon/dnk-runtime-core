from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends, Request

from src.config import dnk_config
from src.modules.communication.application.ports import OutboundMessagePublisherProtocol
from src.modules.communication.application.services import (
    JsonPathService,
    JsonSchemaValidationService,
    ProviderPayloadBuildService,
    ProviderStatusMappingService,
    ProviderYamlLoader,
    SecretCodec,
    TemplateRenderService,
)
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
from src.modules.communication.infrastructure.http_client import HttpxProviderHttpClient
from src.modules.communication.infrastructure.provider_senders import (
    ProviderSenderRegistry,
    YamlHttpProviderSender,
    YamlSmtpProviderSender,
)
from src.modules.communication.infrastructure.rabbitmq import (
    RabbitMQOutboundMessagePublisher,
)
from src.modules.communication.infrastructure.repository import CommunicationRepository
from src.modules.shared.depends.uow import UoWDep


def get_communication_repository(uow: UoWDep) -> CommunicationRepository:
    return CommunicationRepository(uow.session)


CommunicationRepositoryDep = Annotated[
    CommunicationRepository,
    Depends(get_communication_repository),
]


def get_provider_yaml_loader() -> ProviderYamlLoader:
    return ProviderYamlLoader()


def get_schema_validator() -> JsonSchemaValidationService:
    return JsonSchemaValidationService()


def get_secret_codec() -> SecretCodec:
    return SecretCodec()


def get_json_path_service() -> JsonPathService:
    return JsonPathService()


def get_template_render_service() -> TemplateRenderService:
    return TemplateRenderService()


def get_payload_build_service() -> ProviderPayloadBuildService:
    return ProviderPayloadBuildService()


def get_status_mapping_service() -> ProviderStatusMappingService:
    return ProviderStatusMappingService()


def get_http_client() -> HttpxProviderHttpClient:
    return HttpxProviderHttpClient()


ProviderYamlLoaderDep = Annotated[ProviderYamlLoader, Depends(get_provider_yaml_loader)]
JsonSchemaValidationServiceDep = Annotated[
    JsonSchemaValidationService,
    Depends(get_schema_validator),
]
SecretCodecDep = Annotated[SecretCodec, Depends(get_secret_codec)]
JsonPathServiceDep = Annotated[JsonPathService, Depends(get_json_path_service)]
TemplateRenderServiceDep = Annotated[
    TemplateRenderService,
    Depends(get_template_render_service),
]
ProviderPayloadBuildServiceDep = Annotated[
    ProviderPayloadBuildService,
    Depends(get_payload_build_service),
]
ProviderStatusMappingServiceDep = Annotated[
    ProviderStatusMappingService,
    Depends(get_status_mapping_service),
]
HttpClientDep = Annotated[HttpxProviderHttpClient, Depends(get_http_client)]


def get_provider_sender_registry(
    http_client: HttpClientDep,
    payload_builder: ProviderPayloadBuildServiceDep,
    status_mapper: ProviderStatusMappingServiceDep,
    json_path: JsonPathServiceDep,
    secret_codec: SecretCodecDep,
) -> ProviderSenderRegistry:
    return ProviderSenderRegistry(
        [
            YamlHttpProviderSender(
                http_client=http_client,
                payload_builder=payload_builder,
                status_mapper=status_mapper,
                json_path=json_path,
                secret_codec=secret_codec,
            ),
            YamlSmtpProviderSender(
                payload_builder=payload_builder,
                secret_codec=secret_codec,
            ),
        ]
    )


ProviderSenderRegistryDep = Annotated[
    ProviderSenderRegistry,
    Depends(get_provider_sender_registry),
]


async def get_outbound_message_publisher(
    request: Request,
) -> AsyncGenerator[OutboundMessagePublisherProtocol | None, None]:
    if not dnk_config.COMMUNICATION_QUEUE.enabled:
        yield None
        return

    publisher = getattr(request.app.state, "communication_outbound_publisher", None)
    if publisher is not None:
        yield publisher
        return

    async with RabbitMQOutboundMessagePublisher.from_settings(
        dnk_config.COMMUNICATION_QUEUE,
        manage_broker_lifecycle=True,
    ) as fallback_publisher:
        yield fallback_publisher


OutboundMessagePublisherDep = Annotated[
    OutboundMessagePublisherProtocol | None,
    Depends(get_outbound_message_publisher),
]


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
) -> ActivateTemplateVersionUseCase:
    return ActivateTemplateVersionUseCase(repository)


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
) -> SendCommunicationUseCase:
    return SendCommunicationUseCase(repository, schema_validator)


SendCommunicationUseCaseDep = Annotated[
    SendCommunicationUseCase,
    Depends(get_send_communication_use_case),
]


def get_process_outbound_message_use_case(
    repository: CommunicationRepositoryDep,
    sender_registry: ProviderSenderRegistryDep,
    template_renderer: TemplateRenderServiceDep,
) -> ProcessOutboundMessageUseCase:
    return ProcessOutboundMessageUseCase(
        repository=repository,
        sender_registry=sender_registry,
        template_renderer=template_renderer,
    )


ProcessOutboundMessageUseCaseDep = Annotated[
    ProcessOutboundMessageUseCase,
    Depends(get_process_outbound_message_use_case),
]


def get_handle_provider_webhook_use_case(
    repository: CommunicationRepositoryDep,
    json_path: JsonPathServiceDep,
    status_mapper: ProviderStatusMappingServiceDep,
) -> HandleProviderWebhookUseCase:
    return HandleProviderWebhookUseCase(repository, json_path, status_mapper)


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
]
