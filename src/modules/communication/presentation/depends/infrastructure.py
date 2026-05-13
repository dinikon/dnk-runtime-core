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
from src.modules.communication.infrastructure.http_client import HttpxProviderHttpClient
from src.modules.communication.infrastructure.message_template import (
    MessageTemplateQueryRuntimeRepository,
    MessageTemplateRuntimeRepository,
)
from src.modules.communication.infrastructure.provider_senders import (
    ProviderSenderRegistry,
    YamlHttpProviderSender,
    YamlSmtpProviderSender,
)
from src.modules.communication.infrastructure.rabbitmq import (
    RabbitMQOutboundMessagePublisher,
)
from src.modules.communication.infrastructure.repository import CommunicationRepository
from src.modules.runtime_data import PostgresRuntimeGateway, RuntimeFieldTypePolicy
from src.modules.schema_registry.presentation.depends.application import (
    RuntimeObjectResolverDep,
)
from src.modules.shared.depends.uow import UoWDep


def get_runtime_field_type_policy() -> RuntimeFieldTypePolicy:
    return RuntimeFieldTypePolicy()


RuntimeFieldTypePolicyDep = Annotated[
    RuntimeFieldTypePolicy,
    Depends(get_runtime_field_type_policy),
]


def get_runtime_gateway(
    uow: UoWDep,
    type_policy: RuntimeFieldTypePolicyDep,
) -> PostgresRuntimeGateway:
    return PostgresRuntimeGateway(
        uow.session,
        type_policy=type_policy,
    )


RuntimeGatewayDep = Annotated[
    PostgresRuntimeGateway,
    Depends(get_runtime_gateway),
]


def get_communication_repository(
    runtime_object_resolver: RuntimeObjectResolverDep,
    runtime_gateway: RuntimeGatewayDep,
) -> CommunicationRepository:
    return CommunicationRepository(
        runtime_object_resolver=runtime_object_resolver,
        command_gateway=runtime_gateway,
        query_gateway=runtime_gateway,
    )


CommunicationRepositoryDep = Annotated[
    CommunicationRepository,
    Depends(get_communication_repository),
]


def get_message_template_repository(
    runtime_object_resolver: RuntimeObjectResolverDep,
    runtime_gateway: RuntimeGatewayDep,
) -> MessageTemplateRuntimeRepository:
    return MessageTemplateRuntimeRepository(
        runtime_object_resolver=runtime_object_resolver,
        runtime_command_gateway=runtime_gateway,
        runtime_query_gateway=runtime_gateway,
    )


MessageTemplateRuntimeRepositoryDep = Annotated[
    MessageTemplateRuntimeRepository,
    Depends(get_message_template_repository),
]


def get_message_template_query_repository(
    runtime_object_resolver: RuntimeObjectResolverDep,
    runtime_gateway: RuntimeGatewayDep,
) -> MessageTemplateQueryRuntimeRepository:
    return MessageTemplateQueryRuntimeRepository(
        runtime_object_resolver=runtime_object_resolver,
        runtime_query_gateway=runtime_gateway,
    )


MessageTemplateQueryRuntimeRepositoryDep = Annotated[
    MessageTemplateQueryRuntimeRepository,
    Depends(get_message_template_query_repository),
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


__all__ = [
    "CommunicationRepositoryDep",
    "HttpClientDep",
    "JsonPathServiceDep",
    "JsonSchemaValidationServiceDep",
    "MessageTemplateQueryRuntimeRepositoryDep",
    "MessageTemplateRuntimeRepositoryDep",
    "OutboundMessagePublisherDep",
    "ProviderPayloadBuildServiceDep",
    "ProviderSenderRegistryDep",
    "ProviderStatusMappingServiceDep",
    "ProviderYamlLoaderDep",
    "RuntimeFieldTypePolicyDep",
    "RuntimeGatewayDep",
    "SecretCodecDep",
    "TemplateRenderServiceDep",
    "get_communication_repository",
    "get_message_template_repository",
    "get_outbound_message_publisher",
    "get_provider_sender_registry",
    "get_runtime_field_type_policy",
    "get_runtime_gateway",
]
