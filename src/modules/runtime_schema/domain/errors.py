from src.modules.shared.domain.errors import ValidationError


class ObjectMetadataNameImmutableError(ValidationError):
    def __init__(self, name_singular: str):
        super().__init__(
            f"Object metadata name_singular '{name_singular}' is immutable."
        )


class FieldMetadataNameImmutableError(ValidationError):
    def __init__(self, name_field: str):
        super().__init__(f"Field metadata name_field '{name_field}' is immutable.")


class RelationMetadataNotFoundError(ValidationError):
    def __init__(self, relation_id):
        super().__init__(f"Relation metadata '{relation_id}' was not found.")


class RelationFieldAlreadyBoundError(ValidationError):
    def __init__(self, field_id):
        super().__init__(f"Field '{field_id}' is already bound to a relation.")


class RelationJunctionTableAlreadyExistsError(ValidationError):
    def __init__(self, junction_table_name: str):
        super().__init__(
            f"Relation junction table '{junction_table_name}' already exists."
        )


class InvalidRelationFieldTypeError(ValidationError):
    def __init__(self, field_name: str, field_type: str):
        super().__init__(
            f"Field '{field_name}' must be uuid for relation usage, got '{field_type}'."
        )


class CrossTenantRelationError(ValidationError):
    def __init__(self):
        super().__init__("Relation objects and fields must belong to the same tenant.")
