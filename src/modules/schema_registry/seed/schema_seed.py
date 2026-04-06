from src.modules.schema_registry.domain.seed.field_seed import FieldSeed
from src.modules.schema_registry.domain.seed.object_seed import ObjectSeed
from src.modules.schema_registry.domain.seed.schema_seed import SchemaSeed

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
            fields=(
                FieldSeed(
                    name="id",
                    type="uuid",
                    label="ID",
                    description="Contact identifier.",
                    is_nullable=False,
                ),
                FieldSeed(
                    name="last_name",
                    type="text",
                    label="Last Name",
                    description="Contact last name.",
                    is_nullable=False,
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
            ),
        ),
    ),
)
