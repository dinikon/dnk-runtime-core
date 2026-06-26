from __future__ import annotations

import unittest
from datetime import UTC, datetime
from uuid import uuid4

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
    WorkflowApplicationStatusVO,
    WorkflowDefinitionEntity,
    WorkflowEnvironmentVO,
    WorkflowFeaturesVO,
    WorkflowGraphVO,
    WorkflowKindVO,
    WorkflowPayloadVO,
    WorkflowRunEntity,
    WorkflowRunStatusVO,
    WorkflowValidationError,
    WorkflowVersionVO,
)


class WorkflowDomainTests(unittest.TestCase):
    def test_enum_value_objects_normalize_and_reject_unknown_values(self) -> None:
        self.assertEqual(
            WorkflowKindVO.from_value(" broadcast "),
            WorkflowKindVO.BROADCAST,
        )
        self.assertEqual(
            WorkflowApplicationStatusVO.from_value("active"),
            WorkflowApplicationStatusVO.ACTIVE,
        )
        self.assertEqual(
            WorkflowEnvironmentVO.from_value("live"),
            WorkflowEnvironmentVO.LIVE,
        )
        self.assertEqual(
            WorkflowRunStatusVO.from_value("running"),
            WorkflowRunStatusVO.RUNNING,
        )
        self.assertEqual(
            NodeExecutionStatusVO.from_value("skipped"),
            NodeExecutionStatusVO.SKIPPED,
        )

        with self.assertRaises(InvalidWorkflowValueObjectError):
            WorkflowKindVO.from_value("unknown")

    def test_text_value_objects_reject_empty_values(self) -> None:
        self.assertEqual(WorkflowVersionVO(" v1 ").value, "v1")
        self.assertEqual(TriggeredFromVO(" manual ").value, "manual")
        self.assertEqual(NodeIdVO(" start ").value, "start")
        self.assertEqual(NodeTypeVO(" action.send ").value, "action.send")

        for value_object in (
            WorkflowVersionVO,
            TriggeredFromVO,
            NodeIdVO,
            NodeTypeVO,
        ):
            with self.assertRaises(InvalidWorkflowValueObjectError):
                value_object("  ")

    def test_numeric_value_objects_reject_negative_values(self) -> None:
        self.assertEqual(ElapsedTimeVO(1).value, 1.0)
        self.assertEqual(TotalStepsVO(0).value, 0)
        self.assertEqual(NodeIndexVO(0).value, 0)

        for value_object in (ElapsedTimeVO, TotalStepsVO, NodeIndexVO):
            with self.assertRaises(InvalidWorkflowValueObjectError):
                value_object(-1)

    def test_payload_graph_and_features_copy_inputs(self) -> None:
        graph_data = {"nodes": [{"id": "start"}]}
        payload_data = {"contact": {"id": "contact-1"}}
        feature_data = {"enabled": ["send"]}
        feature_list = [{"code": "send"}]

        graph = WorkflowGraphVO(graph_data)
        payload = WorkflowPayloadVO(payload_data)
        features = WorkflowFeaturesVO(feature_data)
        features_list = WorkflowFeaturesVO(feature_list)

        graph_data["nodes"][0]["id"] = "changed"
        payload_data["contact"]["id"] = "changed"
        feature_data["enabled"].append("changed")
        feature_list[0]["code"] = "changed"

        self.assertEqual(graph.value, {"nodes": [{"id": "start"}]})
        self.assertEqual(payload.value, {"contact": {"id": "contact-1"}})
        self.assertEqual(features.value, {"enabled": ["send"]})
        self.assertEqual(features_list.value, [{"code": "send"}])

        with self.assertRaises(InvalidWorkflowValueObjectError):
            WorkflowGraphVO("not-a-mapping")
        with self.assertRaises(InvalidWorkflowValueObjectError):
            WorkflowPayloadVO("not-a-mapping")
        with self.assertRaises(InvalidWorkflowValueObjectError):
            WorkflowFeaturesVO("not-a-config")

    def test_workflow_application_entity_normalizes_raw_values(self) -> None:
        now = datetime(2026, 6, 26, 12, 0, tzinfo=UTC)

        entity = WorkflowApplicationEntity(
            id=uuid4(),
            created_at=now,
            updated_at=now,
            created_by=uuid4(),
            updated_by=uuid4(),
            kind="campaign",
            status="active",
            title="Campaign app",
            description="Campaign orchestrator",
            icon="  megaphone  ",
            icon_background="  #ffffff  ",
            active_workflow_definition_id=None,
        )

        self.assertEqual(entity.kind, WorkflowKindVO.CAMPAIGN)
        self.assertEqual(entity.status, WorkflowApplicationStatusVO.ACTIVE)
        self.assertEqual(entity.title.value, "Campaign app")
        self.assertEqual(entity.description.value, "Campaign orchestrator")
        self.assertEqual(entity.icon.value, "megaphone")
        self.assertEqual(entity.icon_background.value, "#ffffff")

    def test_workflow_definition_entity_normalizes_and_copies_graph_fields(
        self,
    ) -> None:
        now = datetime(2026, 6, 26, 12, 0, tzinfo=UTC)
        graph = {"nodes": [{"id": "question"}]}
        features = {"node_types": ["question", "answer"]}

        entity = WorkflowDefinitionEntity(
            id=uuid4(),
            created_at=now,
            updated_at=now,
            created_by=uuid4(),
            updated_by=uuid4(),
            workflow_application_id=uuid4(),
            version="  v1  ",
            graph=graph,
            features=features,
            environment="live",
            title="Chat flow",
            description="AI chat orchestration",
        )
        graph["nodes"][0]["id"] = "changed"
        features["node_types"].append("changed")

        self.assertEqual(entity.version.value, "v1")
        self.assertEqual(entity.graph.value, {"nodes": [{"id": "question"}]})
        self.assertEqual(entity.features.value, {"node_types": ["question", "answer"]})
        self.assertEqual(entity.environment, WorkflowEnvironmentVO.LIVE)

    def test_workflow_run_entity_normalizes_and_copies_payloads(self) -> None:
        now = datetime(2026, 6, 26, 12, 0, tzinfo=UTC)
        graph = {"nodes": [{"id": "start"}]}
        inputs = {"question": "Hello"}
        outputs = {"answer": "Hi"}

        entity = WorkflowRunEntity(
            id=uuid4(),
            created_at=now,
            updated_at=now,
            finished_at=now,
            workflow_application_id=uuid4(),
            workflow_definition_id=uuid4(),
            triggered_from=" manual ",
            graph=graph,
            status="completed",
            inputs=inputs,
            outputs=outputs,
            error="",
            elapsed_time=1,
            total_steps=2,
        )
        graph["nodes"][0]["id"] = "changed"
        inputs["question"] = "Changed"
        outputs["answer"] = "Changed"

        self.assertEqual(entity.triggered_from.value, "manual")
        self.assertEqual(entity.graph.value, {"nodes": [{"id": "start"}]})
        self.assertEqual(entity.status, WorkflowRunStatusVO.COMPLETED)
        self.assertEqual(entity.inputs.value, {"question": "Hello"})
        self.assertEqual(entity.outputs.value, {"answer": "Hi"})
        self.assertEqual(entity.elapsed_time.value, 1.0)
        self.assertEqual(entity.total_steps.value, 2)

    def test_node_execution_entity_normalizes_and_copies_payloads(self) -> None:
        now = datetime(2026, 6, 26, 12, 0, tzinfo=UTC)
        inputs = {"message": {"text": "Hello"}}
        process_data = {"attempt": 1}
        outputs = {"ok": True}

        entity = NodeExecutionEntity(
            id=uuid4(),
            created_at=now,
            updated_at=now,
            finished_at=now,
            workflow_application_id=uuid4(),
            workflow_definition_id=uuid4(),
            run_id=uuid4(),
            index=0,
            status="completed",
            node_id=" start ",
            node_type=" question ",
            node_title="Question",
            inputs=inputs,
            process_data=process_data,
            outputs=outputs,
            error="",
            elapsed_time=0.25,
        )
        inputs["message"]["text"] = "Changed"
        process_data["attempt"] = 2
        outputs["ok"] = False

        self.assertEqual(entity.index.value, 0)
        self.assertEqual(entity.status, NodeExecutionStatusVO.COMPLETED)
        self.assertEqual(entity.node_id.value, "start")
        self.assertEqual(entity.node_type.value, "question")
        self.assertEqual(entity.node_title.value, "Question")
        self.assertEqual(entity.inputs.value, {"message": {"text": "Hello"}})
        self.assertEqual(entity.process_data.value, {"attempt": 1})
        self.assertEqual(entity.outputs.value, {"ok": True})
        self.assertEqual(entity.elapsed_time.value, 0.25)

    def test_entity_rejects_invalid_datetime_and_payload_values(self) -> None:
        now = datetime(2026, 6, 26, 12, 0, tzinfo=UTC)

        with self.assertRaises(WorkflowValidationError):
            WorkflowDefinitionEntity(
                id=uuid4(),
                created_at="not-datetime",
                updated_at=now,
                created_by=uuid4(),
                updated_by=uuid4(),
                workflow_application_id=uuid4(),
                version="v1",
                graph={},
                features={},
                environment="draft",
                title="Flow",
                description="Description",
            )

        with self.assertRaises(InvalidWorkflowValueObjectError):
            WorkflowRunEntity(
                id=uuid4(),
                created_at=now,
                updated_at=now,
                finished_at=now,
                workflow_application_id=uuid4(),
                workflow_definition_id=uuid4(),
                triggered_from="manual",
                graph={},
                status="running",
                inputs="not-a-payload",
                outputs={},
                error="",
                elapsed_time=0,
                total_steps=0,
            )


if __name__ == "__main__":
    unittest.main()
