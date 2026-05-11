from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.modules.communication.application.services import (
    JsonPathService,
    ProviderPayloadBuildService,
    ProviderStatusMappingService,
    SecretCodec,
    TemplateRenderService,
)
from src.modules.communication.application.use_cases import (
    ProcessOutboundMessageByIdUseCase,
    ProcessOutboundMessageUseCase,
    PublishQueuedOutboundMessagesUseCase,
    RecoverStuckOutboundMessagesUseCase,
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
from src.modules.shared.db.uow import UnitOfWorkProtocol


def build_provider_sender_registry() -> ProviderSenderRegistry:
    payload_builder = ProviderPayloadBuildService()
    secret_codec = SecretCodec()
    return ProviderSenderRegistry(
        [
            YamlHttpProviderSender(
                http_client=HttpxProviderHttpClient(),
                payload_builder=payload_builder,
                status_mapper=ProviderStatusMappingService(),
                json_path=JsonPathService(),
                secret_codec=secret_codec,
            ),
            YamlSmtpProviderSender(
                payload_builder=payload_builder,
                secret_codec=secret_codec,
            ),
        ]
    )


def build_process_outbound_message_use_case(
    *,
    uow: UnitOfWorkProtocol,
) -> ProcessOutboundMessageUseCase:
    """Builds ProcessOutboundMessageUseCase outside FastAPI DI."""
    sender_registry = build_provider_sender_registry()
    return ProcessOutboundMessageUseCase(
        repository=CommunicationRepository(uow.session),
        sender_registry=sender_registry,
        template_renderer=TemplateRenderService(),
    )


def build_process_outbound_message_by_id_use_case(
    *,
    session_factory: async_sessionmaker[AsyncSession],
    processing_lease_seconds: int,
) -> ProcessOutboundMessageByIdUseCase:
    return ProcessOutboundMessageByIdUseCase(
        session_factory=session_factory,
        sender_registry=build_provider_sender_registry(),
        template_renderer=TemplateRenderService(),
        processing_lease_seconds=processing_lease_seconds,
    )


def build_publish_queued_outbound_messages_use_case(
    *,
    uow: UnitOfWorkProtocol,
    publisher: RabbitMQOutboundMessagePublisher,
    republish_after_seconds: int,
) -> PublishQueuedOutboundMessagesUseCase:
    return PublishQueuedOutboundMessagesUseCase(
        repository=CommunicationRepository(uow.session),
        publisher=publisher,
        republish_after_seconds=republish_after_seconds,
    )


def build_recover_stuck_outbound_messages_use_case(
    *,
    uow: UnitOfWorkProtocol,
) -> RecoverStuckOutboundMessagesUseCase:
    return RecoverStuckOutboundMessagesUseCase(
        repository=CommunicationRepository(uow.session),
    )


__all__ = [
    "build_process_outbound_message_by_id_use_case",
    "build_process_outbound_message_use_case",
    "build_provider_sender_registry",
    "build_publish_queued_outbound_messages_use_case",
    "build_recover_stuck_outbound_messages_use_case",
]
