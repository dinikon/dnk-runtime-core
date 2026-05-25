from __future__ import annotations

import unittest
from datetime import UTC, datetime
from types import SimpleNamespace

from src.modules.communication.application.outbound_message import (
    GetOutboundMessageUseCase,
    ListOutboundMessagesUseCase,
    ProcessOutboundMessageUseCase,
    SendCommunicationUseCase,
)
from src.modules.communication.application.services import JsonSchemaValidationService
from src.modules.communication.domain.outbound_message import OutboundMessageService
from src.modules.communication.domain.delivery import DeliveryService
from src.modules.communication.infrastructure.delivery import (
    DeliveryRuntimeRepository,
    OutboundProcessingRuntimeRepository,
)
from src.modules.communication.infrastructure.outbound_message import (
    OutboundMessageRuntimeRepository,
)
from src.modules.communication.presentation.depends.application import (
    get_delivery_service,
    get_get_outbound_message_use_case,
    get_list_outbound_messages_use_case,
    get_outbound_message_service,
    get_outbound_processing_repository,
    get_process_outbound_message_use_case,
    get_send_communication_use_case,
)
from src.modules.communication.presentation.depends.infrastructure import (
    get_delivery_repository,
    get_outbound_message_repository,
)


class _ClockStub:
    def now(self):
        return datetime(2026, 5, 14, 12, 0, tzinfo=UTC)


class OutboundMessageDependsTests(unittest.TestCase):
    def test_outbound_message_dependencies_are_wired(self) -> None:
        repository = get_outbound_message_repository(
            runtime_object_resolver=object(),
            runtime_command_gateway=object(),
            runtime_query_gateway=object(),
        )
        delivery_repository = get_delivery_repository(
            runtime_object_resolver=object(),
            runtime_command_gateway=object(),
            runtime_query_gateway=object(),
            uow=SimpleNamespace(session=object()),
        )
        delivery_service = get_delivery_service(
            repository=delivery_repository,
            clock=_ClockStub(),
        )
        processing_repository = get_outbound_processing_repository(
            outbound_repository=repository,
            delivery_service=delivery_service,
            uow=SimpleNamespace(session=object()),
        )
        service = get_outbound_message_service(
            repository=repository,
            clock=_ClockStub(),
        )
        send_use_case = get_send_communication_use_case(
            repository=repository,
            service=service,
            provider_connection_lookup=object(),
            schema_validator=JsonSchemaValidationService(),
        )
        process_use_case = get_process_outbound_message_use_case(
            repository=processing_repository,
            sender_registry=object(),
            template_renderer=object(),
            clock=_ClockStub(),
        )
        get_use_case = get_get_outbound_message_use_case(repository=repository)
        list_use_case = get_list_outbound_messages_use_case(repository=repository)

        self.assertIsInstance(repository, OutboundMessageRuntimeRepository)
        self.assertIsInstance(delivery_repository, DeliveryRuntimeRepository)
        self.assertIsInstance(delivery_service, DeliveryService)
        self.assertIsInstance(
            processing_repository,
            OutboundProcessingRuntimeRepository,
        )
        self.assertIsInstance(service, OutboundMessageService)
        self.assertIsInstance(send_use_case, SendCommunicationUseCase)
        self.assertIsInstance(process_use_case, ProcessOutboundMessageUseCase)
        self.assertIsInstance(get_use_case, GetOutboundMessageUseCase)
        self.assertIsInstance(list_use_case, ListOutboundMessagesUseCase)


__all__ = ["OutboundMessageDependsTests"]
