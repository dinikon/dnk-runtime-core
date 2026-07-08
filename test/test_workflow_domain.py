from __future__ import annotations

import unittest
from datetime import UTC, datetime
from uuid import uuid4

from src.modules.shared import EntityIdVO
from src.modules.shared.domain.value_object.entity_description import (
    EntityDescriptionVO,
)
from src.modules.shared.domain.value_object.entity_title import EntityTitleVO
from src.modules.workflow.domain import (
    ElapsedTimeVO,
    InvalidWorkflowValueObjectError,
    NodeExecutionEntity,
    NodeExecutionStatusVO,
    NodeIdVO,
    NodeIndexVO,
    NodeTypeVO,
    TotalStepsVO,
    TriggeredFromVO,
    WorkflowApplicationEntity,
    WorkflowApplicationIdVO,
    WorkflowApplicationStatusVO,
    WorkflowDefinitionEntity,
    WorkflowEnvironmentVO,
    WorkflowFeaturesVO,
    WorkflowGraphVO,
    WorkflowIconBackgroundVO,
    WorkflowIconVO,
    WorkflowKindVO,
    WorkflowPayloadVO,
    WorkflowRunEntity,
    WorkflowRunStatusVO,
    WorkflowValidationError,
    WorkflowVersionVO,
)


class WorkflowDomainTests(unittest.TestCase):
    def test_workflow_application_updates_details(self) -> None:
        created_at = datetime(2026, 6, 27, 12, 0, tzinfo=UTC)
        updated_at = datetime(2026, 6, 27, 13, 0, tzinfo=UTC)
        created_by = EntityIdVO.from_value(uuid4())
        updated_by = EntityIdVO.from_value(uuid4())
        entity = WorkflowApplicationEntity.create(
            entity_id=WorkflowApplicationIdVO.from_value(uuid4()),
            kind=WorkflowKindVO.STANDARD,
            title=EntityTitleVO("Customer journey"),
            description=EntityDescriptionVO("Default customer workflow"),
            icon=WorkflowIconVO("workflow"),
            icon_background=WorkflowIconBackgroundVO("#ffffff"),
            created_by=created_by,
            now=created_at,
        )

        entity.update_details(
            title=EntityTitleVO("Updated journey"),
            description=None,
            icon=WorkflowIconVO("sparkles"),
            icon_background=WorkflowIconBackgroundVO("#111111"),
            updated_by=updated_by,
            now=updated_at,
        )

        self.assertEqual(entity.title.value, "Updated journey")
        self.assertIsNone(entity.description)
        self.assertEqual(entity.icon.value, "sparkles")
        self.assertEqual(entity.icon_background.value, "#111111")
        self.assertEqual(entity.created_by, created_by)
        self.assertEqual(entity.created_at, created_at)
        self.assertEqual(entity.updated_by, updated_by)
        self.assertEqual(entity.updated_at, updated_at)


if __name__ == "__main__":
    unittest.main()
