from __future__ import annotations

import unittest
from datetime import UTC, datetime
from uuid import uuid4

from src.modules.tenancy.domain.tenant import TenantStatus
from src.modules.tenancy.domain.tenant.value_object import TenantIdVO
from src.modules.tenancy.domain.tenant_domain import (
    TenantDomainIdVO,
    TenantDomainStatus,
    TenantServiceType,
)
from src.modules.shared import EntityIdVO
from src.modules.tenancy.infrastructure.persistence.tenant import TenantModel
from src.modules.tenancy.infrastructure.persistence.tenant_domain import (
    TenantDomainModel,
)
from src.modules.tenancy.infrastructure.repository.tenant_domain_repository import (
    SqlAlchemyTenantDomainRepository,
)
from src.modules.tenancy.infrastructure.repository.tenant_repository import (
    SqlAlchemyTenantRepository,
)


class _ScalarSequenceResult:
    def __init__(self, items):
        self._items = list(items)

    def one_or_none(self):
        if not self._items:
            return None
        if len(self._items) == 1:
            return self._items[0]
        raise AssertionError("Expected zero or one result in test stub.")

    def all(self):
        return list(self._items)


class _AsyncSessionStub:
    def __init__(self, *, scalars_results=None) -> None:
        self._scalars_results = list(scalars_results or [])

    async def scalars(self, statement):
        if not self._scalars_results:
            return _ScalarSequenceResult([])

        items = self._scalars_results.pop(0)
        if items is None:
            return _ScalarSequenceResult([])
        if isinstance(items, list):
            return _ScalarSequenceResult(items)
        return _ScalarSequenceResult([items])


class SqlAlchemyTenantRepositoryTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.now = datetime.now(UTC)
        self.tenant_id = uuid4()
        self.tenant_model = TenantModel(
            id=self.tenant_id,
            name="Acme",
            external_id="acme",
            status=TenantStatus.ACTIVE,
            custom_config={"theme": "blue"},
            created_at=self.now,
            updated_at=self.now,
        )

    async def test_get_by_id_returns_tenant_from_typed_session_get(self) -> None:
        repository = SqlAlchemyTenantRepository(
            _AsyncSessionStub(scalars_results=[self.tenant_model])
        )

        result = await repository.get_by_id(TenantIdVO.from_value(self.tenant_id))

        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(result.id, TenantIdVO.from_value(self.tenant_id))
        self.assertEqual(result.name, "Acme")
        self.assertEqual(result.external_id, "acme")

    async def test_exists_by_name_returns_true_when_id_found(self) -> None:
        repository = SqlAlchemyTenantRepository(
            _AsyncSessionStub(scalars_results=[self.tenant_id])
        )

        result = await repository.exists_by_name("Acme")

        self.assertTrue(result)


class SqlAlchemyTenantDomainRepositoryTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.now = datetime.now(UTC)
        self.domain_id = uuid4()
        self.tenant_id = uuid4()
        self.domain_model = TenantDomainModel(
            id=self.domain_id,
            tenant_id=self.tenant_id,
            service_type=TenantServiceType.API,
            kind="default",
            host="api.example.com",
            base_path=None,
            auth_mode=None,
            status=TenantDomainStatus.ACTIVE,
            is_primary=True,
            is_wildcard=False,
            parent_domain=None,
            verification_status="verified",
            tls_mode="managed",
            metadata_json=None,
            created_at=self.now,
            updated_at=self.now,
        )

    async def test_get_by_host_returns_domain_from_execute_scalars(self) -> None:
        repository = SqlAlchemyTenantDomainRepository(
            _AsyncSessionStub(scalars_results=[self.domain_model])
        )

        result = await repository.get_by_host("api.example.com")

        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(result.id, TenantDomainIdVO.from_value(self.domain_id))
        self.assertEqual(result.tenant_id, EntityIdVO.from_value(self.tenant_id))
        self.assertEqual(result.host, "api.example.com")
        self.assertEqual(result.service_type, TenantServiceType.API)

    async def test_get_api_host_by_tenant_id_returns_host_string(self) -> None:
        repository = SqlAlchemyTenantDomainRepository(
            _AsyncSessionStub(scalars_results=["api.example.com"])
        )

        result = await repository.get_api_host_by_tenant_id(
            EntityIdVO.from_value(self.tenant_id)
        )

        self.assertEqual(result, "api.example.com")


__all__ = [
    "SqlAlchemyTenantDomainRepositoryTests",
    "SqlAlchemyTenantRepositoryTests",
]
