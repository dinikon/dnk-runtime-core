from __future__ import annotations

import unittest
from datetime import UTC, datetime

from src.modules.communication.application.provider_connector import (
    ListProviderConnectorsUseCase,
    RegisterProviderConnectorUseCase,
)
from src.modules.communication.application.services import ProviderYamlLoader
from src.modules.communication.domain.provider_connector import ProviderConnectorService
from src.modules.communication.infrastructure.provider_connector import (
    ProviderConnectorRuntimeRepository,
)
from src.modules.communication.presentation.depends.application import (
    get_list_provider_connectors_use_case,
    get_provider_connector_service,
    get_register_provider_connector_use_case,
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

        self.assertIsInstance(repository, ProviderConnectorRuntimeRepository)
        self.assertIsInstance(service, ProviderConnectorService)
        self.assertIsInstance(register_use_case, RegisterProviderConnectorUseCase)
        self.assertIsInstance(list_use_case, ListProviderConnectorsUseCase)


__all__ = ["ProviderConnectorDependsTests"]
