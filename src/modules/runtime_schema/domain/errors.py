from src.modules.shared.domain.errors import ValidationError


class ObjectMetadataNotFoundError(ValidationError):
    def __init__(self, object_metadata_id):
        super().__init__(f"Object metadata '{object_metadata_id}' was not found.")


class ObjectMetadataNameImmutableError(ValidationError):
    def __init__(self, name_singular: str):
        super().__init__(
            f"Object metadata name_singular '{name_singular}' is immutable."
        )


class FieldMetadataNotFoundError(ValidationError):
    def __init__(self, field_metadata_id):
        super().__init__(f"Field metadata '{field_metadata_id}' was not found.")


class FieldMetadataNameImmutableError(ValidationError):
    def __init__(self, name_field: str):
        super().__init__(f"Field metadata name_field '{name_field}' is immutable.")


class RelationMetadataNotFoundError(ValidationError):
    def __init__(self, relation_id):
        super().__init__(f"Relation metadata '{relation_id}' was not found.")


class RelationFieldAlreadyBoundError(ValidationError):
    def __init__(self, field_id):
        super().__init__(f"Field '{field_id}' is already bound to a relation.")


class FieldMetadataObjectMismatchError(ValidationError):
    def __init__(self, field_id, object_metadata_id):
        super().__init__(
            f"Field metadata '{field_id}' does not belong to object '{object_metadata_id}'."
        )


class RelationOwnerFieldRequiredError(ValidationError):
    def __init__(self):
        super().__init__("Owner relation must specify source_field_metadata_id.")


class RelationTargetFieldRequiredError(ValidationError):
    def __init__(self):
        super().__init__("Owner relation must specify target_field_metadata_id.")


class InvalidRequiredRelationOnDeleteError(ValidationError):
    def __init__(self, on_delete: str):
        super().__init__("Required relation must not use " f"on_delete='{on_delete}'.")


class RelationJunctionTableAlreadyExistsError(ValidationError):
    def __init__(self, junction_table_name: str):
        super().__init__(
            f"Relation junction table '{junction_table_name}' already exists."
        )


class RelationJunctionTableRequiredError(ValidationError):
    def __init__(self):
        super().__init__("Many-to-many relation must have junction_table_name.")


class InvalidRelationFieldTypeError(ValidationError):
    def __init__(self, field_name: str, field_type: str):
        super().__init__(
            f"Field '{field_name}' must be uuid for relation usage, got '{field_type}'."
        )


class CrossTenantRelationError(ValidationError):
    def __init__(self):
        super().__init__("Relation objects and fields must belong to the same tenant.")


class SystemRelationDefinitionError(ValidationError):
    def __init__(self, object_name_singular: str, field_name: str, reason: str):
        super().__init__(
            "System relation definition "
            f"'{object_name_singular}.{field_name}' is invalid: {reason}."
        )
