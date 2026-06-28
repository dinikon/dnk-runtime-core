from __future__ import annotations

import unittest
from datetime import UTC, datetime
from uuid import uuid4

from src.modules.schema_registry.runtime import (
    RuntimeFieldDescriptor,
    RuntimeObjectDescriptor,
)
from src.modules.shared import EntityIdVO
from src.modules.shared.domain.value_object.entity_description import (
    EntityDescriptionVO,
)
from src.modules.shared.domain.value_object.entity_title import EntityTitleVO
from src.modules.workflow.domain import (
    WorkflowApplicationEntity,
    WorkflowApplicationIdVO,
    WorkflowDefinitionEntity,
    WorkflowDefinitionIdVO,
    WorkflowEnvironmentVO,
    WorkflowFeaturesVO,
    WorkflowGraphVO,
    WorkflowIconBackgroundVO,
    WorkflowIconVO,
    WorkflowKindVO,
)
from src.modules.workflow.infrastructure import WorkflowRuntimeRepository


def _field(
    name: str,
    type_code: str,
    *,
    is_nullable: bool = False,
    default_value: str | None = None,
) -> RuntimeFieldDescriptor:
    return RuntimeFieldDescriptor(
        name=name,
        type_code=type_code,
        is_nullable=is_nullable,
        default_value=default_value,
        options={},
        settings={},
    )


def _application_descriptor() -> RuntimeObjectDescriptor:
    return RuntimeObjectDescriptor(
        schema_name="dnk_test",
        object_name="workflow_application",
        table_name="workflow_applications",
        pk="id",
        title_field="title",
        fields=(
            _field("id", "uuid", default_value="gen_random_uuid()"),
            _field("created_at", "datetime", default_value="CURRENT_TIMESTAMP"),
            _field("updated_at", "datetime", default_value="CURRENT_TIMESTAMP"),
            _field("created_by", "uuid"),
            _field("updated_by", "uuid"),
            _field("kind", "select", default_value="'STANDARD'"),
            _field("status", "select", default_value="'NORMAL'"),
            _field("title", "text"),
            _field("description", "text", is_nullable=True),
            _field("icon", "text"),
            _field("icon_background", "text"),
            _field("active_workflow_definition_id", "uuid", is_nullable=True),
        ),
        relations=(),
    )


def _definition_descriptor() -> RuntimeObjectDescriptor:
    return RuntimeObjectDescriptor(
        schema_name="dnk_test",
        object_name="workflow_definition",
        table_name="workflow_definitions",
        pk="id",
        title_field="title",
        fields=(
            _field("id", "uuid", default_value="gen_random_uuid()"),
            _field("created_at", "datetime", default_value="CURRENT_TIMESTAMP"),
            _field("updated_at", "datetime", default_value="CURRENT_TIMESTAMP"),
            _field("created_by", "uuid"),
            _field("updated_by", "uuid"),
            _field("workflow_application_id", "reference"),
            _field("version", "text", default_value="'draft'"),
            _field("graph", "json", default_value="'{}'"),
            _field("features", "json", default_value="'{}'"),
            _field("environment", "json", default_value="'{}'"),
            _field("title", "text", is_nullable=True),
            _field("description", "text", is_nullable=True),
        ),
        relations=(),
    )


class _ResolverStub:
    def __init__(self) -> None:
        self.calls: list[tuple[EntityIdVO, str]] = []

    async def resolve(self, *, tenant_id, object_name):
        self.calls.append((tenant_id, object_name))
        if object_name == "workflow_application":
            return _application_descriptor()
        if object_name == "workflow_definition":
            return _definition_descriptor()
        raise AssertionError(f"unexpected object name {object_name}")


class _QueryGatewayStub:
    async def get_by_id(self, *, descriptor, object_id, fetch_plan=None):
        return None

    async def list(
        self, *, descriptor, filters=(), sorting=(), page=None, fetch_plan=None
    ):
        return []


class _CommandGatewayStub:
    def __init__(self) -> None:
        self.inserts = []

    async def insert(self, *, descriptor, payload):
        self.inserts.append((descriptor.object_name, payload))
        return {
            **payload,
            "created_at": payload["created_at"],
            "updated_at": payload["updated_at"],
        }

    async def update(self, *, descriptor, object_id, patch):
        raise AssertionError("update should not be called")

    async def delete(self, *, descriptor, object_id):
        return True


class WorkflowRuntimeRepositoryTests(unittest.IsolatedAsyncioTestCase):
    async def test_save_workflow_application_inserts_payload_and_maps_entity(
        self,
    ) -> None:
        tenant_id = EntityIdVO.from_value(uuid4())
        workflow_id = WorkflowApplicationIdVO.from_value(uuid4())
        created_by = EntityIdVO.from_value(uuid4())
        now = datetime.now(UTC)
        resolver = _ResolverStub()
        command_gateway = _CommandGatewayStub()
        repository = WorkflowRuntimeRepository(
            runtime_object_resolver=resolver,
            runtime_command_gateway=command_gateway,
            runtime_query_gateway=_QueryGatewayStub(),
        )
        workflow = WorkflowApplicationEntity.create(
            entity_id=workflow_id,
            kind=WorkflowKindVO.STANDARD,
            title=EntityTitleVO("Customer journey"),
            description=EntityDescriptionVO("Default customer workflow"),
            icon=WorkflowIconVO("workflow"),
            icon_background=WorkflowIconBackgroundVO("#ffffff"),
            created_by=created_by,
            now=now,
        )

        saved = await repository.save(
            tenant_id=tenant_id,
            workflow=workflow,
        )

        self.assertEqual(resolver.calls, [(tenant_id, "workflow_application")])
        self.assertEqual(len(command_gateway.inserts), 1)
        object_name, payload = command_gateway.inserts[0]
        self.assertEqual(object_name, "workflow_application")
        self.assertEqual(payload["id"], workflow_id.uuid)
        self.assertEqual(payload["created_by"], created_by.uuid)
        self.assertEqual(payload["updated_by"], created_by.uuid)
        self.assertEqual(payload["kind"], "STANDARD")
        self.assertEqual(payload["status"], "NORMAL")
        self.assertEqual(payload["title"], "Customer journey")
        self.assertEqual(payload["description"], "Default customer workflow")
        self.assertEqual(payload["icon"], "workflow")
        self.assertEqual(payload["icon_background"], "#ffffff")
        self.assertIsNone(payload["active_workflow_definition_id"])
        self.assertEqual(saved.id, workflow_id)
        self.assertEqual(saved.created_by, created_by)
        self.assertEqual(saved.updated_by, created_by)
        self.assertEqual(saved.title.value, "Customer journey")

    async def test_save_workflow_definition_inserts_payload_and_maps_entity(
        self,
    ) -> None:
        tenant_id = EntityIdVO.from_value(uuid4())
        workflow_id = WorkflowApplicationIdVO.from_value(uuid4())
        definition_id = WorkflowDefinitionIdVO.from_value(uuid4())
        created_by = EntityIdVO.from_value(uuid4())
        now = datetime.now(UTC)
        resolver = _ResolverStub()
        command_gateway = _CommandGatewayStub()
        repository = WorkflowRuntimeRepository(
            runtime_object_resolver=resolver,
            runtime_command_gateway=command_gateway,
            runtime_query_gateway=_QueryGatewayStub(),
        )
        definition = WorkflowDefinitionEntity.create_draft(
            workflow_definition_id=definition_id,
            workflow_application_id=workflow_id,
            graph=WorkflowGraphVO({}),
            features=WorkflowFeaturesVO({}),
            environment=WorkflowEnvironmentVO({}),
            title=None,
            description=None,
            created_by=created_by,
            now=now,
        )

        saved = await repository.save(
            tenant_id=tenant_id,
            definition=definition,
        )

        self.assertEqual(resolver.calls, [(tenant_id, "workflow_definition")])
        self.assertEqual(len(command_gateway.inserts), 1)
        object_name, payload = command_gateway.inserts[0]
        self.assertEqual(object_name, "workflow_definition")
        self.assertEqual(payload["id"], definition_id.uuid)
        self.assertEqual(payload["created_by"], created_by.uuid)
        self.assertEqual(payload["updated_by"], created_by.uuid)
        self.assertEqual(payload["workflow_application_id"], workflow_id.uuid)
        self.assertEqual(payload["version"], "draft")
        self.assertEqual(payload["graph"], {})
        self.assertEqual(payload["features"], {})
        self.assertEqual(payload["environment"], {})
        self.assertIsNone(payload["title"])
        self.assertIsNone(payload["description"])
        self.assertEqual(saved.id, definition_id)
        self.assertEqual(saved.workflow_application_id, workflow_id)
        self.assertEqual(saved.version.value, "draft")
        self.assertEqual(saved.environment.value, {})
        self.assertIsNone(saved.title)


if __name__ == "__main__":
    unittest.main()
