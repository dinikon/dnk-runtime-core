from src.modules.shared.domain.errors import ValidationError


class ObjectMetadataNameImmutableError(ValidationError):
    def __init__(self, name_singular: str):
        super().__init__(
            f"Object metadata name_singular '{name_singular}' is immutable."
        )


class FieldMetadataNameImmutableError(ValidationError):
    def __init__(self, name_field: str):
        super().__init__(f"Field metadata name_field '{name_field}' is immutable.")
