from src.modules.schema_registry.domain.field.value_object.field_kind import FieldKind
from src.modules.schema_registry.domain.object.value_object.object_kind import (
    ObjectKind,
)
from src.modules.schema_registry.domain.seed.field_seed import FieldSeed
from src.modules.schema_registry.domain.seed.index_seed import IndexSeed
from src.modules.schema_registry.domain.seed.object_seed import ObjectSeed
from src.modules.schema_registry.domain.seed.relation_seed import RelationSeed
from src.modules.schema_registry.domain.seed.schema_seed import SchemaSeed


def _id_field(description: str) -> FieldSeed:
    return FieldSeed(
        name="id",
        type="uuid",
        label="ID",
        description=description,
        is_nullable=False,
        default="gen_random_uuid()",
        kind=FieldKind.SYSTEM,
    )


def _created_at_field() -> FieldSeed:
    return FieldSeed(
        name="created_at",
        type="datetime",
        label="Created At",
        description="Record creation timestamp.",
        is_nullable=False,
        default="CURRENT_TIMESTAMP",
        kind=FieldKind.SYSTEM,
    )


def _updated_at_field() -> FieldSeed:
    return FieldSeed(
        name="updated_at",
        type="datetime",
        label="Updated At",
        description="Record update timestamp.",
        is_nullable=False,
        default="CURRENT_TIMESTAMP",
        kind=FieldKind.SYSTEM,
    )


def _system_fields(description: str) -> tuple[FieldSeed, FieldSeed, FieldSeed]:
    return (_id_field(description), _created_at_field(), _updated_at_field())


COMMUNICATION_OBJECTS = (
    ObjectSeed(
        singular_name="communication_provider_connector",
        plural_name="communication_provider_connectors",
        singular_label="Communication Provider Connector",
        plural_label="Communication Provider Connectors",
        description="Tenant-local YAML provider connector definitions.",
        kind=ObjectKind.SYSTEM,
        fields=(
            *_system_fields("Provider connector identifier."),
            FieldSeed("provider_code", "text", "Provider Code", is_nullable=False),
            FieldSeed("provider_name", "text", "Provider Name", is_nullable=False),
            FieldSeed("version", "text", "Version", is_nullable=False),
            FieldSeed("connector_type", "text", "Connector Type", is_nullable=False),
            FieldSeed("yaml_spec", "json", "YAML Spec", is_nullable=False),
            FieldSeed("yaml_checksum", "text", "YAML Checksum", is_nullable=False),
            FieldSeed(
                "status",
                "text",
                "Status",
                description="Provider connector lifecycle: ACTIVE, DISABLED, ARCHIVED.",
                is_nullable=False,
                default="'ACTIVE'",
            ),
        ),
        indexes=(
            IndexSeed("communication_provider_connectors_id_uq", ("id",), True),
            IndexSeed(
                "communication_provider_connectors_code_version_uq",
                ("provider_code", "version"),
                True,
            ),
            IndexSeed(
                "communication_provider_connectors_provider_code_idx",
                ("provider_code",),
            ),
            IndexSeed("communication_provider_connectors_status_idx", ("status",)),
        ),
    ),
    ObjectSeed(
        singular_name="communication_provider_message_type",
        plural_name="communication_provider_message_types",
        singular_label="Communication Provider Message Type",
        plural_label="Communication Provider Message Types",
        description="Tenant-local provider message type schemas.",
        kind=ObjectKind.SYSTEM,
        fields=(
            *_system_fields("Provider message type identifier."),
            FieldSeed(
                "provider_connector_id",
                "reference",
                "Provider Connector ID",
                is_nullable=False,
            ),
            FieldSeed(
                "message_type_code", "text", "Message Type Code", is_nullable=False
            ),
            FieldSeed("channel_code", "text", "Channel Code", is_nullable=False),
            FieldSeed("name", "text", "Name", is_nullable=False),
            FieldSeed("field_schema", "json", "Field Schema", is_nullable=False),
            FieldSeed(
                "ui_schema",
                "json",
                "UI Schema",
                is_nullable=False,
                default="'{}'",
            ),
            FieldSeed(
                "is_active",
                "bool",
                "Is Active",
                is_nullable=False,
                default="true",
            ),
        ),
        indexes=(
            IndexSeed("communication_provider_message_types_id_uq", ("id",), True),
            IndexSeed(
                "communication_provider_message_types_connector_code_uq",
                ("provider_connector_id", "message_type_code"),
                True,
            ),
            IndexSeed(
                "communication_provider_message_types_channel_idx",
                ("channel_code",),
            ),
        ),
        relations=(
            RelationSeed(
                name="communication_provider_message_types_connector",
                relation_type="many_to_one",
                source_object="communication_provider_message_type",
                target_object="communication_provider_connector",
                owning_object="communication_provider_message_type",
                fk_field="provider_connector_id",
                referenced_object="communication_provider_connector",
                referenced_field="id",
                on_delete="cascade",
            ),
        ),
    ),
    ObjectSeed(
        singular_name="communication_provider_connection",
        plural_name="communication_provider_connections",
        singular_label="Communication Provider Connection",
        plural_label="Communication Provider Connections",
        description="Tenant-local provider credentials and configuration.",
        kind=ObjectKind.SYSTEM,
        fields=(
            *_system_fields("Provider connection identifier."),
            FieldSeed(
                "provider_connector_id",
                "reference",
                "Provider Connector ID",
                is_nullable=False,
            ),
            FieldSeed("connection_name", "text", "Connection Name", is_nullable=False),
            FieldSeed("channel_code", "text", "Channel Code", is_nullable=False),
            FieldSeed("config", "json", "Config", is_nullable=False, default="'{}'"),
            FieldSeed("secret_ref", "text", "Secret Ref", is_nullable=True),
            FieldSeed("secrets_b64", "text", "Encoded Secrets", is_nullable=True),
            FieldSeed(
                "status",
                "text",
                "Status",
                description="Provider connection lifecycle: ACTIVE, DISABLED, ARCHIVED.",
                is_nullable=False,
                default="'ACTIVE'",
            ),
        ),
        indexes=(
            IndexSeed("communication_provider_connections_id_uq", ("id",), True),
            IndexSeed(
                "communication_provider_connections_connector_idx",
                ("provider_connector_id",),
            ),
            IndexSeed(
                "communication_provider_connections_channel_idx", ("channel_code",)
            ),
            IndexSeed("communication_provider_connections_status_idx", ("status",)),
        ),
        relations=(
            RelationSeed(
                name="communication_provider_connections_connector",
                relation_type="many_to_one",
                source_object="communication_provider_connection",
                target_object="communication_provider_connector",
                owning_object="communication_provider_connection",
                fk_field="provider_connector_id",
                referenced_object="communication_provider_connector",
                referenced_field="id",
                on_delete="restrict",
            ),
        ),
    ),
    ObjectSeed(
        singular_name="communication_message_template",
        plural_name="communication_message_templates",
        singular_label="Communication Message Template",
        plural_label="Communication Message Templates",
        description="Tenant-local communication template headers.",
        kind=ObjectKind.SYSTEM,
        fields=(
            *_system_fields("Message template identifier."),
            FieldSeed("name", "text", "Name", is_nullable=False),
            FieldSeed("description", "text", "Description", is_nullable=True),
            FieldSeed(
                "provider_connector_id",
                "reference",
                "Provider Connector ID",
                is_nullable=False,
            ),
            FieldSeed(
                "provider_message_type_id",
                "reference",
                "Provider Message Type ID",
                is_nullable=False,
            ),
            FieldSeed("channel_code", "text", "Channel Code", is_nullable=False),
            FieldSeed("status", "text", "Status", is_nullable=False, default="'DRAFT'"),
        ),
        indexes=(
            IndexSeed("communication_message_templates_id_uq", ("id",), True),
            IndexSeed(
                "communication_message_templates_connector_idx",
                ("provider_connector_id",),
            ),
            IndexSeed(
                "communication_message_templates_message_type_idx",
                ("provider_message_type_id",),
            ),
            IndexSeed("communication_message_templates_channel_idx", ("channel_code",)),
            IndexSeed("communication_message_templates_status_idx", ("status",)),
        ),
        relations=(
            RelationSeed(
                name="communication_message_templates_connector",
                relation_type="many_to_one",
                source_object="communication_message_template",
                target_object="communication_provider_connector",
                owning_object="communication_message_template",
                fk_field="provider_connector_id",
                referenced_object="communication_provider_connector",
                referenced_field="id",
                on_delete="restrict",
            ),
            RelationSeed(
                name="communication_message_templates_message_type",
                relation_type="many_to_one",
                source_object="communication_message_template",
                target_object="communication_provider_message_type",
                owning_object="communication_message_template",
                fk_field="provider_message_type_id",
                referenced_object="communication_provider_message_type",
                referenced_field="id",
                on_delete="restrict",
            ),
        ),
    ),
    ObjectSeed(
        singular_name="communication_template_version",
        plural_name="communication_template_versions",
        singular_label="Communication Template Version",
        plural_label="Communication Template Versions",
        description="Tenant-local versioned communication template payloads.",
        kind=ObjectKind.SYSTEM,
        fields=(
            *_system_fields("Template version identifier."),
            FieldSeed("template_id", "reference", "Template ID", is_nullable=False),
            FieldSeed("version", "datetime", "Version", is_nullable=False),
            FieldSeed(
                "template_payload", "json", "Template Payload", is_nullable=False
            ),
            FieldSeed(
                "variables_schema",
                "json",
                "Variables Schema",
                is_nullable=False,
                default="'{}'",
            ),
            FieldSeed("status", "text", "Status", is_nullable=False, default="'DRAFT'"),
            FieldSeed("activated_at", "datetime", "Activated At", is_nullable=True),
        ),
        indexes=(
            IndexSeed("communication_template_versions_id_uq", ("id",), True),
            IndexSeed(
                "communication_template_versions_template_version_uq",
                ("template_id", "version"),
                True,
            ),
            IndexSeed("communication_template_versions_template_idx", ("template_id",)),
            IndexSeed("communication_template_versions_status_idx", ("status",)),
        ),
        relations=(
            RelationSeed(
                name="communication_template_versions_template",
                relation_type="many_to_one",
                source_object="communication_template_version",
                target_object="communication_message_template",
                owning_object="communication_template_version",
                fk_field="template_id",
                referenced_object="communication_message_template",
                referenced_field="id",
                on_delete="cascade",
            ),
        ),
    ),
    ObjectSeed(
        singular_name="communication_request",
        plural_name="communication_requests",
        singular_label="Communication Request",
        plural_label="Communication Requests",
        description="Tenant-local inbound communication send commands.",
        kind=ObjectKind.SYSTEM,
        fields=(
            *_system_fields("Communication request identifier."),
            FieldSeed("initiator_type", "text", "Initiator Type", is_nullable=False),
            FieldSeed("initiator_ref_id", "text", "Initiator Ref ID", is_nullable=True),
            FieldSeed("correlation_id", "uuid", "Correlation ID", is_nullable=True),
            FieldSeed("idempotency_key", "text", "Idempotency Key", is_nullable=True),
            FieldSeed("channel_code", "text", "Channel Code", is_nullable=False),
            FieldSeed("template_id", "reference", "Template ID", is_nullable=False),
            FieldSeed(
                "template_version_id",
                "reference",
                "Template Version ID",
                is_nullable=False,
            ),
            FieldSeed(
                "recipient_identifier_type",
                "text",
                "Recipient Identifier Type",
                is_nullable=True,
            ),
            FieldSeed(
                "recipient_address", "text", "Recipient Address", is_nullable=False
            ),
            FieldSeed(
                "recipient_snapshot",
                "json",
                "Recipient Snapshot",
                is_nullable=False,
                default="'{}'",
            ),
            FieldSeed(
                "variables", "json", "Variables", is_nullable=False, default="'{}'"
            ),
            FieldSeed("scheduled_at", "datetime", "Scheduled At", is_nullable=True),
            FieldSeed("priority", "int", "Priority", is_nullable=False, default="100"),
            FieldSeed(
                "status", "text", "Status", is_nullable=False, default="'ACCEPTED'"
            ),
        ),
        indexes=(
            IndexSeed("communication_requests_id_uq", ("id",), True),
            IndexSeed(
                "communication_requests_idempotency_uq", ("idempotency_key",), True
            ),
            IndexSeed("communication_requests_channel_idx", ("channel_code",)),
            IndexSeed("communication_requests_status_idx", ("status",)),
        ),
        relations=(
            RelationSeed(
                name="communication_requests_template",
                relation_type="many_to_one",
                source_object="communication_request",
                target_object="communication_message_template",
                owning_object="communication_request",
                fk_field="template_id",
                referenced_object="communication_message_template",
                referenced_field="id",
                on_delete="restrict",
            ),
            RelationSeed(
                name="communication_requests_template_version",
                relation_type="many_to_one",
                source_object="communication_request",
                target_object="communication_template_version",
                owning_object="communication_request",
                fk_field="template_version_id",
                referenced_object="communication_template_version",
                referenced_field="id",
                on_delete="restrict",
            ),
        ),
    ),
    ObjectSeed(
        singular_name="communication_outbound_message",
        plural_name="communication_outbound_messages",
        singular_label="Communication Outbound Message",
        plural_label="Communication Outbound Messages",
        description="Tenant-local concrete outbound provider messages.",
        kind=ObjectKind.SYSTEM,
        fields=(
            *_system_fields("Outbound message identifier."),
            FieldSeed(
                "communication_request_id",
                "reference",
                "Communication Request ID",
                is_nullable=False,
            ),
            FieldSeed(
                "provider_connection_id",
                "reference",
                "Provider Connection ID",
                is_nullable=False,
            ),
            FieldSeed("channel_code", "text", "Channel Code", is_nullable=False),
            FieldSeed("priority", "int", "Priority", is_nullable=False, default="100"),
            FieldSeed(
                "recipient_identifier_type",
                "text",
                "Recipient Identifier Type",
                is_nullable=True,
            ),
            FieldSeed(
                "recipient_address", "text", "Recipient Address", is_nullable=False
            ),
            FieldSeed(
                "recipient_snapshot",
                "json",
                "Recipient Snapshot",
                is_nullable=False,
                default="'{}'",
            ),
            FieldSeed(
                "rendered_payload",
                "json",
                "Rendered Payload",
                is_nullable=False,
                default="'{}'",
            ),
            FieldSeed(
                "provider_request_payload",
                "json",
                "Provider Request Payload",
                is_nullable=False,
                default="'{}'",
            ),
            FieldSeed(
                "external_message_id", "text", "External Message ID", is_nullable=True
            ),
            FieldSeed("external_status", "text", "External Status", is_nullable=True),
            FieldSeed(
                "internal_status",
                "text",
                "Internal Status",
                is_nullable=False,
                default="'QUEUED'",
            ),
            FieldSeed("error_code", "text", "Error Code", is_nullable=True),
            FieldSeed("error_message", "text", "Error Message", is_nullable=True),
            FieldSeed("queued_at", "datetime", "Queued At", is_nullable=True),
            FieldSeed("sent_at", "datetime", "Sent At", is_nullable=True),
            FieldSeed("delivered_at", "datetime", "Delivered At", is_nullable=True),
            FieldSeed("failed_at", "datetime", "Failed At", is_nullable=True),
            FieldSeed("processing_token", "uuid", "Processing Token", is_nullable=True),
            FieldSeed(
                "processing_started_at",
                "datetime",
                "Processing Started At",
                is_nullable=True,
            ),
            FieldSeed(
                "processing_deadline_at",
                "datetime",
                "Processing Deadline At",
                is_nullable=True,
            ),
            FieldSeed(
                "next_attempt_at", "datetime", "Next Attempt At", is_nullable=True
            ),
            FieldSeed(
                "queue_published_at", "datetime", "Queue Published At", is_nullable=True
            ),
            FieldSeed(
                "queue_publish_count",
                "int",
                "Queue Publish Count",
                is_nullable=False,
                default="0",
            ),
        ),
        indexes=(
            IndexSeed("communication_outbound_messages_id_uq", ("id",), True),
            IndexSeed(
                "communication_outbound_messages_request_idx",
                ("communication_request_id",),
            ),
            IndexSeed(
                "communication_outbound_messages_connection_idx",
                ("provider_connection_id",),
            ),
            IndexSeed("communication_outbound_messages_channel_idx", ("channel_code",)),
            IndexSeed(
                "communication_outbound_messages_external_idx", ("external_message_id",)
            ),
            IndexSeed(
                "communication_outbound_messages_internal_status_idx",
                ("internal_status",),
            ),
            IndexSeed(
                "communication_outbound_messages_processing_token_idx",
                ("processing_token",),
            ),
            IndexSeed(
                "communication_outbound_messages_processing_deadline_idx",
                ("processing_deadline_at",),
            ),
            IndexSeed(
                "communication_outbound_messages_next_attempt_idx", ("next_attempt_at",)
            ),
            IndexSeed(
                "communication_outbound_messages_queue_published_idx",
                ("queue_published_at",),
            ),
        ),
        relations=(
            RelationSeed(
                name="communication_outbound_messages_request",
                relation_type="many_to_one",
                source_object="communication_outbound_message",
                target_object="communication_request",
                owning_object="communication_outbound_message",
                fk_field="communication_request_id",
                referenced_object="communication_request",
                referenced_field="id",
                on_delete="cascade",
            ),
            RelationSeed(
                name="communication_outbound_messages_connection",
                relation_type="many_to_one",
                source_object="communication_outbound_message",
                target_object="communication_provider_connection",
                owning_object="communication_outbound_message",
                fk_field="provider_connection_id",
                referenced_object="communication_provider_connection",
                referenced_field="id",
                on_delete="restrict",
            ),
        ),
    ),
    ObjectSeed(
        singular_name="communication_delivery_attempt",
        plural_name="communication_delivery_attempts",
        singular_label="Communication Delivery Attempt",
        plural_label="Communication Delivery Attempts",
        description="Tenant-local provider send attempts.",
        kind=ObjectKind.SYSTEM,
        fields=(
            _id_field("Delivery attempt identifier."),
            FieldSeed(
                "outbound_message_id",
                "reference",
                "Outbound Message ID",
                is_nullable=False,
            ),
            FieldSeed(
                "provider_connection_id",
                "reference",
                "Provider Connection ID",
                is_nullable=False,
            ),
            FieldSeed("attempt_no", "int", "Attempt No", is_nullable=False),
            FieldSeed("status", "text", "Status", is_nullable=False),
            FieldSeed("request_payload", "json", "Request Payload", is_nullable=True),
            FieldSeed("response_payload", "json", "Response Payload", is_nullable=True),
            FieldSeed("http_status_code", "int", "HTTP Status Code", is_nullable=True),
            FieldSeed(
                "external_message_id", "text", "External Message ID", is_nullable=True
            ),
            FieldSeed("error_code", "text", "Error Code", is_nullable=True),
            FieldSeed("error_message", "text", "Error Message", is_nullable=True),
            FieldSeed(
                "started_at",
                "datetime",
                "Started At",
                is_nullable=False,
                default="CURRENT_TIMESTAMP",
                kind=FieldKind.SYSTEM,
            ),
            FieldSeed("finished_at", "datetime", "Finished At", is_nullable=True),
        ),
        indexes=(
            IndexSeed("communication_delivery_attempts_id_uq", ("id",), True),
            IndexSeed(
                "communication_delivery_attempts_outbound_attempt_uq",
                ("outbound_message_id", "attempt_no"),
                True,
            ),
            IndexSeed(
                "communication_delivery_attempts_outbound_idx", ("outbound_message_id",)
            ),
            IndexSeed("communication_delivery_attempts_status_idx", ("status",)),
        ),
        relations=(
            RelationSeed(
                name="communication_delivery_attempts_outbound",
                relation_type="many_to_one",
                source_object="communication_delivery_attempt",
                target_object="communication_outbound_message",
                owning_object="communication_delivery_attempt",
                fk_field="outbound_message_id",
                referenced_object="communication_outbound_message",
                referenced_field="id",
                on_delete="cascade",
            ),
            RelationSeed(
                name="communication_delivery_attempts_connection",
                relation_type="many_to_one",
                source_object="communication_delivery_attempt",
                target_object="communication_provider_connection",
                owning_object="communication_delivery_attempt",
                fk_field="provider_connection_id",
                referenced_object="communication_provider_connection",
                referenced_field="id",
                on_delete="restrict",
            ),
        ),
    ),
    ObjectSeed(
        singular_name="communication_delivery_event",
        plural_name="communication_delivery_events",
        singular_label="Communication Delivery Event",
        plural_label="Communication Delivery Events",
        description="Tenant-local provider delivery status events.",
        kind=ObjectKind.SYSTEM,
        fields=(
            _id_field("Delivery event identifier."),
            _created_at_field(),
            FieldSeed(
                "outbound_message_id",
                "reference",
                "Outbound Message ID",
                is_nullable=True,
            ),
            FieldSeed(
                "provider_connection_id",
                "reference",
                "Provider Connection ID",
                is_nullable=True,
            ),
            FieldSeed(
                "external_message_id", "text", "External Message ID", is_nullable=True
            ),
            FieldSeed("external_status", "text", "External Status", is_nullable=True),
            FieldSeed("internal_status", "text", "Internal Status", is_nullable=False),
            FieldSeed("event_type", "text", "Event Type", is_nullable=False),
            FieldSeed("event_at", "datetime", "Event At", is_nullable=True),
            FieldSeed(
                "raw_payload", "json", "Raw Payload", is_nullable=False, default="'{}'"
            ),
        ),
        indexes=(
            IndexSeed("communication_delivery_events_id_uq", ("id",), True),
            IndexSeed(
                "communication_delivery_events_outbound_idx", ("outbound_message_id",)
            ),
            IndexSeed(
                "communication_delivery_events_external_idx", ("external_message_id",)
            ),
            IndexSeed(
                "communication_delivery_events_internal_status_idx",
                ("internal_status",),
            ),
            IndexSeed("communication_delivery_events_type_idx", ("event_type",)),
        ),
        relations=(
            RelationSeed(
                name="communication_delivery_events_outbound",
                relation_type="many_to_one",
                source_object="communication_delivery_event",
                target_object="communication_outbound_message",
                owning_object="communication_delivery_event",
                fk_field="outbound_message_id",
                referenced_object="communication_outbound_message",
                referenced_field="id",
                on_delete="set_null",
            ),
            RelationSeed(
                name="communication_delivery_events_connection",
                relation_type="many_to_one",
                source_object="communication_delivery_event",
                target_object="communication_provider_connection",
                owning_object="communication_delivery_event",
                fk_field="provider_connection_id",
                referenced_object="communication_provider_connection",
                referenced_field="id",
                on_delete="set_null",
            ),
        ),
    ),
)


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
                is_nullable=False,
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


SCHEMA_SEED = SchemaSeed(
    version=None,
    code="crm",
    label="CRM",
    objects=(
        ObjectSeed(
            singular_name="contact",
            plural_name="contacts",
            singular_label="Contact",
            plural_label="Contacts",
            description="Tenant contact registry.",
            kind=ObjectKind.STANDARD,
            fields=(
                FieldSeed(
                    name="id",
                    type="uuid",
                    label="ID",
                    description="Contact identifier.",
                    is_nullable=False,
                    default="gen_random_uuid()",
                    kind=FieldKind.SYSTEM,
                ),
                FieldSeed(
                    name="created_at",
                    type="datetime",
                    label="Created At",
                    description="Record creation timestamp.",
                    is_nullable=False,
                    default="CURRENT_TIMESTAMP",
                    kind=FieldKind.SYSTEM,
                ),
                FieldSeed(
                    name="updated_at",
                    type="datetime",
                    label="Updated At",
                    description="Record update timestamp.",
                    is_nullable=False,
                    default="CURRENT_TIMESTAMP",
                    kind=FieldKind.SYSTEM,
                ),
                FieldSeed(
                    name="last_name",
                    type="text",
                    label="Last Name",
                    description="Contact last name.",
                    is_nullable=True,
                ),
                FieldSeed(
                    name="first_name",
                    type="text",
                    label="First Name",
                    description="Contact first name.",
                    is_nullable=False,
                ),
                FieldSeed(
                    name="middle_name",
                    type="text",
                    label="Middle Name",
                    description="Contact middle name.",
                    is_nullable=True,
                ),
                FieldSeed(
                    name="status",
                    type="select",
                    label="Status",
                    description="Contact status.",
                    is_nullable=False,
                    default="'lead'",
                    options={
                        "lead": "Lead",
                        "customer": "Customer",
                        "partner": "Partner",
                    },
                ),
                FieldSeed(
                    name="tags",
                    type="multiselect",
                    label="Tags",
                    description="Contact tags.",
                    is_nullable=True,
                    options={
                        "vip": "VIP",
                        "newsletter": "Newsletter",
                        "inactive": "Inactive",
                    },
                ),
            ),
            indexes=(
                IndexSeed(
                    name="contacts_id_uq",
                    fields=("id",),
                    is_unique=True,
                ),
            ),
            relations=(
                RelationSeed(
                    name="contact_companies",
                    relation_type="many_to_many",
                    source_object="contact",
                    target_object="company",
                    source_relation_name="companies",
                    target_relation_name="contacts",
                    relation_table_name="contacts_companies",
                    source_join_column_name="contact_id",
                    target_join_column_name="company_id",
                    on_delete="restrict",
                ),
            ),
        ),
        ObjectSeed(
            singular_name="company",
            plural_name="companies",
            singular_label="Company",
            plural_label="Companies",
            description="Tenant company registry.",
            kind=ObjectKind.STANDARD,
            fields=(
                *_system_fields("Company identifier."),
                FieldSeed(
                    name="legal_name",
                    type="text",
                    label="Legal Name",
                    description="Company legal name.",
                    is_nullable=False,
                    default="'Unknown Company'",
                ),
            ),
            indexes=(
                IndexSeed(
                    name="companies_id_uq",
                    fields=("id",),
                    is_unique=True,
                ),
                IndexSeed(
                    name="companies_legal_name_idx",
                    fields=("legal_name",),
                    is_unique=False,
                ),
            ),
        ),
        ObjectSeed(
            singular_name="contact_point",
            plural_name="contact_points",
            singular_label="Contact Point",
            plural_label="Contact Points",
            description="Tenant contact point registry.",
            kind=ObjectKind.STANDARD,
            fields=(
                *_system_fields("Contact point identifier."),
                FieldSeed(
                    name="contact_point_type",
                    type="text",
                    label="Contact Point Type",
                    description="Contact point channel or type.",
                    is_nullable=False,
                ),
                FieldSeed(
                    name="raw_value",
                    type="text",
                    label="Raw Value",
                    description="Original contact point value.",
                    is_nullable=False,
                ),
                FieldSeed(
                    name="normalized_value",
                    type="text",
                    label="Normalized Value",
                    description="Canonical contact point value.",
                    is_nullable=False,
                ),
                FieldSeed(
                    name="normalized_hash",
                    type="text",
                    label="Normalized Hash",
                    description="Hash of the normalized contact point value.",
                    is_nullable=False,
                ),
            ),
            indexes=(
                IndexSeed(
                    name="uniq_contact_point_type_hash",
                    fields=("contact_point_type", "normalized_hash"),
                    is_unique=True,
                ),
                IndexSeed(
                    name="idx_contact_point_hash",
                    fields=("normalized_hash",),
                    is_unique=False,
                ),
            ),
        ),
        ObjectSeed(
            singular_name="contact_point_binding",
            plural_name="contact_point_bindings",
            singular_label="Contact Point Binding",
            plural_label="Contact Point Bindings",
            description="Tenant contact point ownership bindings.",
            kind=ObjectKind.STANDARD,
            fields=(
                *_system_fields("Contact point binding identifier."),
                FieldSeed(
                    name="contact_point_id",
                    type="reference",
                    label="Contact Point ID",
                    description="Bound contact point identifier.",
                    is_nullable=False,
                ),
                FieldSeed(
                    name="contact_point_type",
                    type="text",
                    label="Contact Point Type",
                    description="Denormalized contact point channel or type.",
                    is_nullable=False,
                ),
                FieldSeed(
                    name="owner_object_id",
                    type="uuid",
                    label="Owner Object ID",
                    description="Runtime object identifier for the binding owner.",
                    is_nullable=False,
                ),
                FieldSeed(
                    name="owner_record_id",
                    type="uuid",
                    label="Owner Record ID",
                    description="Runtime record identifier for the binding owner.",
                    is_nullable=False,
                ),
                FieldSeed(
                    name="is_primary",
                    type="bool",
                    label="Is Primary",
                    description="Whether this contact point is primary for the owner and type.",
                    is_nullable=False,
                    default="false",
                ),
                FieldSeed(
                    name="is_active",
                    type="bool",
                    label="Is Active",
                    description="Whether this owner binding is currently active.",
                    is_nullable=False,
                    default="true",
                ),
                FieldSeed(
                    name="detached_at",
                    type="datetime",
                    label="Detached At",
                    description="Timestamp of soft detach.",
                    is_nullable=True,
                ),
            ),
            indexes=(
                IndexSeed(
                    name="idx_cpb_owner",
                    fields=("owner_object_id", "owner_record_id"),
                    is_unique=False,
                ),
                IndexSeed(
                    name="idx_cpb_contact_point_id",
                    fields=("contact_point_id",),
                    is_unique=False,
                ),
                IndexSeed(
                    name="idx_cpb_owner_type",
                    fields=("owner_object_id", "owner_record_id", "contact_point_type"),
                    is_unique=False,
                ),
                IndexSeed(
                    name="uniq_cpb_point_owner",
                    fields=(
                        "contact_point_id",
                        "owner_object_id",
                        "owner_record_id",
                    ),
                    is_unique=True,
                ),
            ),
            relations=(
                RelationSeed(
                    name="contact_point_bindings_contact_point",
                    relation_type="many_to_one",
                    source_object="contact_point_binding",
                    target_object="contact_point",
                    owning_object="contact_point_binding",
                    fk_field="contact_point_id",
                    referenced_object="contact_point",
                    referenced_field="id",
                    on_delete="restrict",
                ),
            ),
        ),
        *WORKFLOW_OBJECTS,
        *COMMUNICATION_OBJECTS,
    ),
)
