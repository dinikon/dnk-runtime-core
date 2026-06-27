from src.modules.schema_registry.domain.object.value_object.object_kind import (
    ObjectKind,
)
from src.modules.schema_registry.domain.seed.field_seed import FieldSeed
from src.modules.schema_registry.domain.seed.index_seed import IndexSeed
from src.modules.schema_registry.domain.seed.object_seed import ObjectSeed
from src.modules.schema_registry.domain.seed.relation_seed import RelationSeed
from src.modules.schema_registry.seed.common import _system_fields

CONTACT_POINT_OBJECTS = (
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
)


__all__ = ["CONTACT_POINT_OBJECTS"]
