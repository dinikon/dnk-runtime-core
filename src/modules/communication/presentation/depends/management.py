from __future__ import annotations

from src.modules.communication.application.services import (
    JsonPathService,
    ProviderPayloadBuildService,
    ProviderStatusMappingService,
    SecretCodec,
    TemplateRenderService,
)
from src.modules.communication.application.use_cases import (
    ProcessOutboundMessageUseCase,
)
from src.modules.communication.infrastructure.http_client import HttpxProviderHttpClient
from src.modules.communication.infrastructure.provider_senders import (
    ProviderSenderRegistry,
    YamlHttpProviderSender,
    YamlSmtpProviderSender,
)
from src.modules.communication.infrastructure.repository import CommunicationRepository
from src.modules.shared.db.uow import UnitOfWorkProtocol


def build_process_outbound_message_use_case(
    *,
    uow: UnitOfWorkProtocol,
) -> ProcessOutboundMessageUseCase:
    """Builds ProcessOutboundMessageUseCase outside FastAPI DI."""
    payload_builder = ProviderPayloadBuildService()
    secret_codec = SecretCodec()
    sender_registry = ProviderSenderRegistry(
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
    return ProcessOutboundMessageUseCase(
        repository=CommunicationRepository(uow.session),
        sender_registry=sender_registry,
        template_renderer=TemplateRenderService(),
    )


__all__ = ["build_process_outbound_message_use_case"]
