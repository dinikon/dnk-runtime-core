from src.modules.schema_registry.domain.object.value_object.object_kind import (
    ObjectKind,
)
from src.modules.schema_registry.domain.seed.field_seed import FieldSeed
from src.modules.schema_registry.domain.seed.index_seed import IndexSeed
from src.modules.schema_registry.domain.seed.object_seed import ObjectSeed
from src.modules.schema_registry.domain.seed.relation_seed import RelationSeed
from src.modules.schema_registry.seed.common import _system_fields

WORKFLOW_OBJECTS = (
    ObjectSeed(
        singular_name="workflow_application",
        plural_name="workflow_applications",
        singular_label="Workflow Application",
        plural_label="Workflow Applications",
        description="Tenant-local workflow application headers.",
        kind=ObjectKind.SYSTEM,
        fields=(
            *_system_fields("Workflow application identifier."),
            FieldSeed(
                name="created_by",
                type="uuid",
                label="Created By",
                description="User that created the workflow application.",
                is_nullable=False,
            ),
            FieldSeed(
                name="updated_by",
                type="uuid",
                label="Updated By",
                description="User that last updated the workflow application.",
                is_nullable=False,
            ),
            FieldSeed(
                name="kind",
                type="select",
                label="Kind",
                description="Workflow orchestration kind.",
                is_nullable=False,
                default="'STANDARD'",
                options={
                    "STANDARD": "Standard",
                    "BROADCAST": "Broadcast",
                    "CAMPAIGN": "Campaign",
                },
            ),
            FieldSeed(
                name="status",
                type="select",
                label="Status",
                description="Workflow application lifecycle status.",
                is_nullable=False,
                default="'NORMAL'",
                options={"NORMAL": "Normal"},
            ),
            FieldSeed(
                name="title",
                type="text",
                label="Title",
                description="Workflow display title.",
                is_nullable=False,
            ),
            FieldSeed(
                name="description",
                type="text",
                label="Description",
                description="Optional workflow description.",
                is_nullable=True,
            ),
            FieldSeed(
                name="icon",
                type="text",
                label="Icon",
                description="Workflow icon identifier.",
                is_nullable=False,
            ),
            FieldSeed(
                name="icon_background",
                type="text",
                label="Icon Background",
                description="Workflow icon background value.",
                is_nullable=False,
            ),
            FieldSeed(
                name="active_workflow_definition_id",
                type="uuid",
                label="Active Workflow Definition ID",
                description="Currently active workflow definition identifier.",
                is_nullable=True,
            ),
        ),
        indexes=(
            IndexSeed("workflow_applications_id_uq", ("id",), True),
            IndexSeed("workflow_applications_kind_status_idx", ("kind", "status")),
            IndexSeed("workflow_applications_status_idx", ("status",)),
        ),
    ),
    ObjectSeed(
        singular_name="workflow_definition",
        plural_name="workflow_definitions",
        singular_label="Workflow Definition",
        plural_label="Workflow Definitions",
        description="Tenant-local versioned workflow graph definitions.",
        kind=ObjectKind.SYSTEM,
        fields=(
            *_system_fields("Workflow definition identifier."),
            FieldSeed(
                name="created_by",
                type="uuid",
                label="Created By",
                description="User that created the workflow definition.",
                is_nullable=False,
            ),
            FieldSeed(
                name="updated_by",
                type="uuid",
                label="Updated By",
                description="User that last updated the workflow definition.",
                is_nullable=False,
            ),
            FieldSeed(
                name="workflow_application_id",
                type="reference",
                label="Workflow Application ID",
                description="Owning workflow application identifier.",
                is_nullable=False,
            ),
            FieldSeed(
                name="version",
                type="text",
                label="Version",
                description="Workflow definition version label.",
                is_nullable=False,
                default="'draft'",
            ),
            FieldSeed(
                name="graph",
                type="json",
                label="Graph",
                description="Workflow graph snapshot.",
                is_nullable=False,
                default="'{}'",
            ),
            FieldSeed(
                name="features",
                type="json",
                label="Features",
                description="Workflow feature configuration snapshot.",
                is_nullable=False,
                default="'{}'",
            ),
            FieldSeed(
                name="environment",
                type="json",
                label="Environment",
                description="Workflow environment configuration snapshot.",
                is_nullable=False,
                default="'{}'",
            ),
            FieldSeed(
                name="title",
                type="text",
                label="Title",
                description="Workflow definition display title.",
                is_nullable=True,
            ),
            FieldSeed(
                name="description",
                type="text",
                label="Description",
                description="Optional workflow definition description.",
                is_nullable=True,
            ),
        ),
        indexes=(
            IndexSeed("workflow_definitions_id_uq", ("id",), True),
            IndexSeed(
                "workflow_definitions_application_version_uq",
                ("workflow_application_id", "version"),
                True,
            ),
        ),
        relations=(
            RelationSeed(
                name="workflow_definitions_application",
                relation_type="many_to_one",
                source_object="workflow_definition",
                target_object="workflow_application",
                owning_object="workflow_definition",
                fk_field="workflow_application_id",
                referenced_object="workflow_application",
                referenced_field="id",
                on_delete="restrict",
            ),
        ),
    ),
)


__all__ = ["WORKFLOW_OBJECTS"]
