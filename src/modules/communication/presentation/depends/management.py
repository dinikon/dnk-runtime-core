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
from src.modules.communication.infrastructure.outbound_message import (
    OutboundMessageRuntimeRepository,
    OutboundProcessingRepositoryContextFactory,
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
from src.modules.schema_registry.domain.field.type_catalog import FieldTypeCatalog
from src.modules.schema_registry.domain.datasource.service import DataSourceService
from src.modules.schema_registry.domain.datasource.value_object import DataSourceIdVO
from src.modules.schema_registry.domain.field.value_object import RuntimeFieldIdVO
from src.modules.schema_registry.domain.object.service import ObjectService
from src.modules.schema_registry.domain.object.value_object import RuntimeObjectIdVO
from src.modules.schema_registry.infrastructure.repository.data_source_repository import (
    SqlAlchemyDataSourceRepository,
)
from src.modules.schema_registry.infrastructure.repository.object_repository import (
    SqlAlchemyObjectRepository,
)
from src.modules.schema_registry.runtime import SchemaRegistryRuntimeObjectResolver
from src.modules.shared.db.uow import UnitOfWorkProtocol
from src.modules.shared.infrastructure.time.utc_clock import UtcClock
import uuid6


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
    clock = UtcClock()
    return ProcessOutboundMessageUseCase(
        repository=build_outbound_message_repository(uow.session),
        sender_registry=sender_registry,
        template_renderer=TemplateRenderService(),
        clock=clock,
    )


def build_process_outbound_message_by_id_use_case(
    *,
    session_factory: async_sessionmaker[AsyncSession],
    processing_lease_seconds: int,
) -> ProcessOutboundMessageByIdUseCase:
    clock = UtcClock()
    return ProcessOutboundMessageByIdUseCase(
        repository_context_factory=OutboundProcessingRepositoryContextFactory(
            session_factory=session_factory,
            repository_factory=build_outbound_message_repository,
        ),
        sender_registry=build_provider_sender_registry(),
        template_renderer=TemplateRenderService(),
        processing_lease_seconds=processing_lease_seconds,
        clock=clock,
    )


def build_publish_queued_outbound_messages_use_case(
    *,
    uow: UnitOfWorkProtocol,
    publisher: RabbitMQOutboundMessagePublisher,
    republish_after_seconds: int,
) -> PublishQueuedOutboundMessagesUseCase:
    clock = UtcClock()
    return PublishQueuedOutboundMessagesUseCase(
        repository=build_outbound_message_repository(uow.session),
        publisher=publisher,
        republish_after_seconds=republish_after_seconds,
        clock=clock,
    )


def build_recover_stuck_outbound_messages_use_case(
    *,
    uow: UnitOfWorkProtocol,
) -> RecoverStuckOutboundMessagesUseCase:
    clock = UtcClock()
    return RecoverStuckOutboundMessagesUseCase(
        repository=build_outbound_message_repository(uow.session),
        clock=clock,
    )


def build_communication_repository(session: AsyncSession) -> CommunicationRepository:
    clock = UtcClock()
    field_type_catalog = FieldTypeCatalog()
    data_source_service = DataSourceService(
        repository=SqlAlchemyDataSourceRepository(session),
        clock=clock,
        id_provider=lambda: DataSourceIdVO.from_value(uuid6.uuid7()),
    )
    object_service = ObjectService(
        object_repository=SqlAlchemyObjectRepository(session),
        clock=clock,
        object_id_provider=lambda: RuntimeObjectIdVO.from_value(uuid6.uuid7()),
        field_id_provider=lambda: RuntimeFieldIdVO.from_value(uuid6.uuid7()),
        field_type_catalog=field_type_catalog,
    )
    runtime_gateway = PostgresRuntimeGateway(
        session,
        type_policy=RuntimeFieldTypePolicy(),
    )
    return CommunicationRepository(
        runtime_object_resolver=SchemaRegistryRuntimeObjectResolver(
            data_source_service=data_source_service,
            object_service=object_service,
        ),
        command_gateway=runtime_gateway,
        query_gateway=runtime_gateway,
    )


def build_outbound_message_repository(
    session: AsyncSession,
) -> OutboundMessageRuntimeRepository:
    """Builds outbound message runtime repository outside FastAPI DI."""
    clock = UtcClock()
    field_type_catalog = FieldTypeCatalog()
    data_source_service = DataSourceService(
        repository=SqlAlchemyDataSourceRepository(session),
        clock=clock,
        id_provider=lambda: DataSourceIdVO.from_value(uuid6.uuid7()),
    )
    object_service = ObjectService(
        object_repository=SqlAlchemyObjectRepository(session),
        clock=clock,
        object_id_provider=lambda: RuntimeObjectIdVO.from_value(uuid6.uuid7()),
        field_id_provider=lambda: RuntimeFieldIdVO.from_value(uuid6.uuid7()),
        field_type_catalog=field_type_catalog,
    )
    runtime_gateway = PostgresRuntimeGateway(
        session,
        type_policy=RuntimeFieldTypePolicy(),
    )
    return OutboundMessageRuntimeRepository(
        runtime_object_resolver=SchemaRegistryRuntimeObjectResolver(
            data_source_service=data_source_service,
            object_service=object_service,
        ),
        runtime_command_gateway=runtime_gateway,
        runtime_query_gateway=runtime_gateway,
    )


__all__ = [
    "build_process_outbound_message_by_id_use_case",
    "build_process_outbound_message_use_case",
    "build_communication_repository",
    "build_outbound_message_repository",
    "build_provider_sender_registry",
    "build_publish_queued_outbound_messages_use_case",
    "build_recover_stuck_outbound_messages_use_case",
]
