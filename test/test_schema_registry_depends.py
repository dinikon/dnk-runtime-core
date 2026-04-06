from __future__ import annotations

import unittest
from types import SimpleNamespace

from src.modules.schema_registry.presentation.depends.infrastructure import (
    get_data_source_repository,
    get_tenant_schema_executor,
    get_tenant_schema_inspector,
)
from src.modules.tenancy.presentation.depends.infrastructure import (
    get_tenants_repository,
)


class SessionBoundDependsTests(unittest.TestCase):
    def test_repositories_and_adapters_share_the_same_session_object(self) -> None:
        session = object()
        uow = SimpleNamespace(session=session)

        tenants_repository = get_tenants_repository(uow)
        data_source_repository = get_data_source_repository(uow)
        schema_executor = get_tenant_schema_executor(uow)
        schema_inspector = get_tenant_schema_inspector(uow)

        self.assertIs(tenants_repository._session, session)
        self.assertIs(data_source_repository._session, session)
        self.assertIs(schema_executor._session, session)
        self.assertIs(schema_inspector._session, session)
