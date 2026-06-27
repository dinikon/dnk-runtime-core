from __future__ import annotations

import unittest
from datetime import UTC, datetime

from src.modules.communication.application.provider_connection import (
    CreateProviderConnectionUseCase,
    DeleteProviderConnectionUseCase,
    ListProviderConnectionsUseCase,
    UpdateProviderConnectionStatusUseCase,
)
from src.modules.communication.application.services import (
    JsonSchemaValidationService,
    SecretCodec,
)
from src.modules.communication.domain.provider_connection import (
    ProviderConnectionService,
)
from src.modules.communication.infrastructure.provider_connection import (
    ProviderConnectionRuntimeRepository,
)
from src.modules.communication.presentation.depends.application import (
    get_create_provider_connection_use_case,
    get_delete_provider_connection_use_case,
    get_list_provider_connections_use_case,
    get_provider_connection_service,
    get_update_provider_connection_status_use_case,
)
from src.modules.communication.presentation.depends.infrastructure import (
    get_provider_connection_repository,
)


class _ClockStub:
    def now(self):
        return datetime(2026, 5, 13, 12, 0, tzinfo=UTC)


class ProviderConnectionDependsTests(unittest.TestCase):
    def test_provider_connection_dependencies_are_wired(self) -> None:
        repository = get_provider_connection_repository(
            runtime_object_resolver=object(),
            runtime_command_gateway=object(),
            runtime_query_gateway=object(),
        )
        service = get_provider_connection_service(
            repository=repository,
            schema_validator=JsonSchemaValidationService(),
            clock=_ClockStub(),
        )
        create_use_case = get_create_provider_connection_use_case(
            service=service,
            secret_codec=SecretCodec(),
        )
        list_use_case = get_list_provider_connections_use_case(repository=repository)
        update_status_use_case = get_update_provider_connection_status_use_case(
            service=service
        )
        delete_use_case = get_delete_provider_connection_use_case(service=service)

        self.assertIsInstance(repository, ProviderConnectionRuntimeRepository)
        self.assertIsInstance(service, ProviderConnectionService)
        self.assertIsInstance(create_use_case, CreateProviderConnectionUseCase)
        self.assertIsInstance(list_use_case, ListProviderConnectionsUseCase)
        self.assertIsInstance(
            update_status_use_case,
            UpdateProviderConnectionStatusUseCase,
        )
        self.assertIsInstance(delete_use_case, DeleteProviderConnectionUseCase)


__all__ = ["ProviderConnectionDependsTests"]
