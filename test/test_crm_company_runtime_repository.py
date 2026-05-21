from __future__ import annotations

import unittest
from datetime import UTC, datetime
from uuid import uuid4

from src.modules.crm.domain.company.error import CompanyNotFoundError
from src.modules.crm.domain.company.value_object import CompanyIdVO
from src.modules.crm.infrastructure import CompanyRuntimeRepository
from src.modules.schema_registry.runtime import (
    RuntimeFieldDescriptor,
    RuntimeObjectDescriptor,
)
from src.modules.shared import EntityIdVO


def _descriptor() -> RuntimeObjectDescriptor:
    return RuntimeObjectDescriptor(
        schema_name="dnk_test",
        object_name="company",
        table_name="companies",
        pk="id",
        title_field="id",
        fields=(
            RuntimeFieldDescriptor(
                name="id",
                type_code="uuid",
                is_nullable=False,
                default_value="gen_random_uuid()",
                options={},
                settings={},
            ),
            RuntimeFieldDescriptor(
                name="created_at",
                type_code="datetime",
                is_nullable=False,
                default_value="CURRENT_TIMESTAMP",
                options={},
                settings={},
            ),
            RuntimeFieldDescriptor(
                name="updated_at",
                type_code="datetime",
                is_nullable=False,
                default_value="CURRENT_TIMESTAMP",
                options={},
                settings={},
            ),
            RuntimeFieldDescriptor(
                name="legal_name",
                type_code="text",
                is_nullable=False,
                default_value=None,
                options={},
                settings={},
            ),
        ),
        relations=(),
    )


class CompanyRuntimeRepositoryTests(unittest.IsolatedAsyncioTestCase):
    async def test_save_inserts_when_row_is_missing(self) -> None:
        tenant_id = EntityIdVO.from_value(uuid4())
        company_id = CompanyIdVO.from_value(uuid4())
        now = datetime.now(UTC)

        class ResolverStub:
            async def resolve(self, *, tenant_id, object_name):
                return _descriptor()

        class QueryGatewayStub:
            async def get_by_id(self, *, descriptor, object_id, fetch_plan=None):
                return None

            async def list(
                self, *, descriptor, filters=(), sorting=(), page=None, fetch_plan=None
            ):
                return []

        inserted_payload = None

        class CommandGatewayStub:
            async def insert(self, *, descriptor, payload):
                nonlocal inserted_payload
                inserted_payload = payload
                return {
                    "id": company_id.uuid,
                    "created_at": now,
                    "updated_at": now,
                    "legal_name": "Acme LLC",
                }

            async def update(self, *, descriptor, object_id, patch):
                return None

            async def delete(self, *, descriptor, object_id):
                return True

        repository = CompanyRuntimeRepository(
            runtime_object_resolver=ResolverStub(),
            runtime_command_gateway=CommandGatewayStub(),
            runtime_query_gateway=QueryGatewayStub(),
        )

        company = await repository.save(
            tenant_id=tenant_id,
            company=type(
                "CompanyStub",
                (),
                {
                    "id": company_id,
                    "legal_name": type("LegalName", (), {"value": "Acme LLC"})(),
                },
            )(),
        )

        self.assertEqual(inserted_payload["id"], company_id.uuid)
        self.assertEqual(inserted_payload["legal_name"], "Acme LLC")
        self.assertEqual(company.id.uuid, company_id.uuid)
        self.assertEqual(company.legal_name.value, "Acme LLC")

    async def test_save_updates_legal_name_when_row_exists(self) -> None:
        tenant_id = EntityIdVO.from_value(uuid4())
        company_id = CompanyIdVO.from_value(uuid4())
        now = datetime.now(UTC)

        class ResolverStub:
            async def resolve(self, *, tenant_id, object_name):
                return _descriptor()

        class QueryGatewayStub:
            async def get_by_id(self, *, descriptor, object_id, fetch_plan=None):
                return {
                    "id": company_id.uuid,
                    "created_at": now,
                    "updated_at": now,
                    "legal_name": "Acme LLC",
                }

            async def list(
                self, *, descriptor, filters=(), sorting=(), page=None, fetch_plan=None
            ):
                return []

        updated_patch = None

        class CommandGatewayStub:
            async def insert(self, *, descriptor, payload):
                raise AssertionError("insert should not be called")

            async def update(self, *, descriptor, object_id, patch):
                nonlocal updated_patch
                updated_patch = patch
                return {
                    "id": company_id.uuid,
                    "created_at": now,
                    "updated_at": now,
                    "legal_name": "Acme Inc.",
                }

            async def delete(self, *, descriptor, object_id):
                return True

        repository = CompanyRuntimeRepository(
            runtime_object_resolver=ResolverStub(),
            runtime_command_gateway=CommandGatewayStub(),
            runtime_query_gateway=QueryGatewayStub(),
        )

        company = await repository.save(
            tenant_id=tenant_id,
            company=type(
                "CompanyStub",
                (),
                {
                    "id": company_id,
                    "legal_name": type("LegalName", (), {"value": "Acme Inc."})(),
                },
            )(),
        )

        self.assertEqual(updated_patch["legal_name"], "Acme Inc.")
        self.assertEqual(company.legal_name.value, "Acme Inc.")

    async def test_get_by_id_maps_runtime_row_to_dto(self) -> None:
        tenant_id = EntityIdVO.from_value(uuid4())
        company_id = CompanyIdVO.from_value(uuid4())
        now = datetime.now(UTC)

        class ResolverStub:
            async def resolve(self, *, tenant_id, object_name):
                return _descriptor()

        class CommandGatewayStub:
            async def insert(self, *, descriptor, payload):
                raise AssertionError("insert should not be called")

            async def update(self, *, descriptor, object_id, patch):
                raise AssertionError("update should not be called")

            async def delete(self, *, descriptor, object_id):
                return True

        class QueryGatewayStub:
            async def get_by_id(self, *, descriptor, object_id, fetch_plan=None):
                return {
                    "id": company_id.uuid,
                    "created_at": now,
                    "updated_at": now,
                    "legal_name": "Acme LLC",
                }

            async def list(
                self, *, descriptor, filters=(), sorting=(), page=None, fetch_plan=None
            ):
                return []

        repository = CompanyRuntimeRepository(
            runtime_object_resolver=ResolverStub(),
            runtime_command_gateway=CommandGatewayStub(),
            runtime_query_gateway=QueryGatewayStub(),
        )

        dto = await repository.get_by_id(
            tenant_id=tenant_id,
            company_id=company_id,
        )

        self.assertIsNotNone(dto)
        assert dto is not None
        self.assertEqual(dto.id, company_id.uuid)
        self.assertEqual(dto.legal_name, "Acme LLC")

    async def test_delete_raises_when_nothing_removed(self) -> None:
        tenant_id = EntityIdVO.from_value(uuid4())
        company_id = CompanyIdVO.from_value(uuid4())

        class ResolverStub:
            async def resolve(self, *, tenant_id, object_name):
                return _descriptor()

        class CommandGatewayStub:
            async def insert(self, *, descriptor, payload):
                return {}

            async def update(self, *, descriptor, object_id, patch):
                return None

            async def delete(self, *, descriptor, object_id):
                return False

        class QueryGatewayStub:
            async def get_by_id(self, *, descriptor, object_id, fetch_plan=None):
                return None

            async def list(
                self, *, descriptor, filters=(), sorting=(), page=None, fetch_plan=None
            ):
                return []

        repository = CompanyRuntimeRepository(
            runtime_object_resolver=ResolverStub(),
            runtime_command_gateway=CommandGatewayStub(),
            runtime_query_gateway=QueryGatewayStub(),
        )

        with self.assertRaises(CompanyNotFoundError):
            await repository.delete(
                tenant_id=tenant_id,
                company_id=company_id,
            )
