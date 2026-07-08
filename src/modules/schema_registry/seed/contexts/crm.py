from src.modules.schema_registry.domain.field.value_object.field_kind import FieldKind
from src.modules.schema_registry.domain.object.value_object.object_kind import (
    ObjectKind,
)
from src.modules.schema_registry.domain.seed.field_seed import FieldSeed
from src.modules.schema_registry.domain.seed.index_seed import IndexSeed
from src.modules.schema_registry.domain.seed.object_seed import ObjectSeed
from src.modules.schema_registry.domain.seed.relation_seed import RelationSeed
from src.modules.schema_registry.seed.common import _system_fields

CRM_OBJECTS = (
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
)


__all__ = ["CRM_OBJECTS"]
