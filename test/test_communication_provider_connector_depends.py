from __future__ import annotations

import unittest
from datetime import UTC, datetime

from src.modules.communication.application.provider_connector import (
    DeleteProviderConnectorUseCase,
    ListProviderConnectorsUseCase,
    RegisterProviderConnectorUseCase,
    UpdateProviderConnectorStatusUseCase,
)
from src.modules.communication.application.services import ProviderYamlLoader
from src.modules.communication.domain.provider_connector import ProviderConnectorService
from src.modules.communication.infrastructure.provider_connector import (
    ProviderConnectorRuntimeRepository,
)
from src.modules.communication.presentation.depends.application import (
    get_delete_provider_connector_use_case,
    get_list_provider_connectors_use_case,
    get_provider_connector_service,
    get_register_provider_connector_use_case,
    get_update_provider_connector_status_use_case,
)
from src.modules.communication.presentation.depends.infrastructure import (
    get_provider_connector_repository,
)


class _ClockStub:
    def now(self):
        return datetime(2026, 5, 13, 12, 0, tzinfo=UTC)


class ProviderConnectorDependsTests(unittest.TestCase):
    def test_provider_connector_dependencies_are_wired(self) -> None:
        repository = get_provider_connector_repository(
            runtime_object_resolver=object(),
            runtime_command_gateway=object(),
            runtime_query_gateway=object(),
        )
        service = get_provider_connector_service(
            repository=repository,
            clock=_ClockStub(),
        )
        register_use_case = get_register_provider_connector_use_case(
            service=service,
            loader=ProviderYamlLoader(),
        )
        list_use_case = get_list_provider_connectors_use_case(repository=repository)
        update_status_use_case = get_update_provider_connector_status_use_case(
            service=service
        )
        delete_use_case = get_delete_provider_connector_use_case(service=service)

        self.assertIsInstance(repository, ProviderConnectorRuntimeRepository)
        self.assertIsInstance(service, ProviderConnectorService)
        self.assertIsInstance(register_use_case, RegisterProviderConnectorUseCase)
        self.assertIsInstance(list_use_case, ListProviderConnectorsUseCase)
        self.assertIsInstance(
            update_status_use_case,
            UpdateProviderConnectorStatusUseCase,
        )
        self.assertIsInstance(delete_use_case, DeleteProviderConnectorUseCase)


__all__ = ["ProviderConnectorDependsTests"]
