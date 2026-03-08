from __future__ import annotations

from collections.abc import Sequence

from src.modules.runtime_schema.application.bootstrap_tenant_system_schema.ports.system_definitions import (
    SystemObjectDefinitionsProviderProtocol,
)
from src.modules.runtime_schema.domain.entities import (
    SystemFieldDefinition,
    SystemObjectDefinition,
)
from src.modules.runtime_schema.domain.value_objects.field_type import (
    RuntimeSchemaFieldType,
)
from src.modules.runtime_schema.domain.value_objects.relation_kind import (
    RuntimeSchemaRelationKind,
)
from src.modules.runtime_schema.domain.value_objects.relation_on_delete import (
    RuntimeSchemaRelationOnDelete,
)


def _tenant_system_fields() -> tuple[SystemFieldDefinition, ...]:
    return (
        SystemFieldDefinition(
            name_field="id",
            column_name="id",
            field_type=RuntimeSchemaFieldType.UUID,
            label="ID",
            is_nullable=False,
            is_unique=True,
            is_ui_read_only=True,
            is_primary_key=True,
        ),
        SystemFieldDefinition(
            name_field="title",
            column_name="title",
            field_type=RuntimeSchemaFieldType.STRING,
            label="Title",
            is_nullable=False,
        ),
        SystemFieldDefinition(
            name_field="created_by",
            column_name="created_by",
            field_type=RuntimeSchemaFieldType.UUID,
            label="Created By",
            is_nullable=False,
            is_ui_read_only=True,
        ),
        SystemFieldDefinition(
            name_field="updated_by",
            column_name="updated_by",
            field_type=RuntimeSchemaFieldType.UUID,
            label="Updated By",
            is_nullable=False,
            is_ui_read_only=True,
        ),
        SystemFieldDefinition(
            name_field="created_at",
            column_name="created_at",
            field_type=RuntimeSchemaFieldType.DATETIME,
            label="Created At",
            is_nullable=False,
            is_ui_read_only=True,
            default_sql="CURRENT_TIMESTAMP",
        ),
        SystemFieldDefinition(
            name_field="updated_at",
            column_name="updated_at",
            field_type=RuntimeSchemaFieldType.DATETIME,
            label="Updated At",
            is_nullable=False,
            is_ui_read_only=True,
            default_sql="CURRENT_TIMESTAMP",
        ),
    )


class StaticSystemObjectDefinitionsProvider(SystemObjectDefinitionsProviderProtocol):
    def get_system_objects(self) -> Sequence[SystemObjectDefinition]:
        common_fields = _tenant_system_fields()
        return (
            SystemObjectDefinition(
                name_singular="deal",
                name_plural="deals",
                label_singular="Deal",
                label_plural="Deals",
                table_name="crm_deals",
                label_identifier_field_name="title",
                fields=(
                    *common_fields,
                    SystemFieldDefinition(
                        name_field="assigned_user_id",
                        column_name="assigned_user_id",
                        field_type=RuntimeSchemaFieldType.UUID,
                        label="Assigned User",
                        is_nullable=True,
                    ),
                ),
                description="System CRM deal entity.",
                icon="briefcase",
                is_audit_logged=True,
                shortcut="D",
            ),
            SystemObjectDefinition(
                name_singular="company",
                name_plural="companies",
                label_singular="Company",
                label_plural="Companies",
                table_name="crm_companies",
                label_identifier_field_name="title",
                fields=(
                    *common_fields,
                    SystemFieldDefinition(
                        name_field="assigned_user_id",
                        column_name="assigned_user_id",
                        field_type=RuntimeSchemaFieldType.UUID,
                        label="Assigned User",
                        is_nullable=True,
                    ),
                ),
                description="System CRM company entity.",
                icon="building",
                is_audit_logged=True,
            ),
            SystemObjectDefinition(
                name_singular="contact",
                name_plural="contacts",
                label_singular="Contact",
                label_plural="Contacts",
                table_name="crm_contacts",
                label_identifier_field_name="title",
                fields=(
                    *common_fields,
                    SystemFieldDefinition(
                        name_field="assigned_user_id",
                        column_name="assigned_user_id",
                        field_type=RuntimeSchemaFieldType.UUID,
                        label="Assigned User",
                        is_nullable=True,
                    ),
                    SystemFieldDefinition(
                        name_field="last_name",
                        column_name="last_name",
                        field_type=RuntimeSchemaFieldType.STRING,
                        label="Last Name",
                        is_nullable=True,
                    ),
                    SystemFieldDefinition(
                        name_field="first_name",
                        column_name="first_name",
                        field_type=RuntimeSchemaFieldType.STRING,
                        label="First Name",
                        is_nullable=True,
                    ),
                    SystemFieldDefinition(
                        name_field="middle_name",
                        column_name="middle_name",
                        field_type=RuntimeSchemaFieldType.STRING,
                        label="Middle Name",
                        is_nullable=True,
                    ),
                ),
                description="System CRM contact entity.",
                icon="user",
                is_audit_logged=True,
            ),
            SystemObjectDefinition(
                name_singular="lead",
                name_plural="leads",
                label_singular="Lead",
                label_plural="Leads",
                table_name="crm_leads",
                label_identifier_field_name="title",
                fields=(
                    *common_fields,
                    SystemFieldDefinition(
                        name_field="assigned_user_id",
                        column_name="assigned_user_id",
                        field_type=RuntimeSchemaFieldType.UUID,
                        label="Assigned User",
                        is_nullable=True,
                    ),
                    SystemFieldDefinition(
                        name_field="contact_id",
                        column_name="contact_id",
                        field_type=RuntimeSchemaFieldType.UUID,
                        label="Contact",
                        is_nullable=True,
                        relation_kind=RuntimeSchemaRelationKind.MANY_TO_ONE,
                        relation_target_object_name_singular="contact",
                        relation_target_field_name="id",
                        reverse_name_field="leads",
                        reverse_label="Leads",
                        relation_on_delete=RuntimeSchemaRelationOnDelete.SET_NULL,
                    ),
                    SystemFieldDefinition(
                        name_field="company_id",
                        column_name="company_id",
                        field_type=RuntimeSchemaFieldType.UUID,
                        label="Company",
                        is_nullable=True,
                        relation_kind=RuntimeSchemaRelationKind.MANY_TO_ONE,
                        relation_target_object_name_singular="company",
                        relation_target_field_name="id",
                        reverse_name_field="leads",
                        reverse_label="Leads",
                        relation_on_delete=RuntimeSchemaRelationOnDelete.SET_NULL,
                    ),
                ),
                description="System CRM lead entity.",
                icon="sparkles",
                is_audit_logged=True,
                shortcut="L",
            ),
        )
