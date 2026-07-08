from src.modules.schema_registry.domain.field.value_object.field_kind import FieldKind
from src.modules.schema_registry.domain.seed.field_seed import FieldSeed


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


__all__ = [
    "_created_at_field",
    "_id_field",
    "_system_fields",
    "_updated_at_field",
]
