from modules.shared.domain.errors import ValidationError


class FieldNameRequiredError(ValidationError):
    def __init__(self) -> None:
        super().__init__("field_name is required")


class FieldNameInvalidFormatError(ValidationError):
    def __init__(self, value: str) -> None:
        super().__init__(
            f"field_name '{value}' has invalid format; expected snake_case"
        )


class FieldLabelRequiredError(ValidationError):
    def __init__(self) -> None:
        super().__init__("field label is required")


class FieldUniqueMustBeIndexedError(ValidationError):
    def __init__(self) -> None:
        super().__init__("unique field must also be indexed")


class FieldOptionsRequiredError(ValidationError):
    def __init__(self, field_type: str, expected: str) -> None:
        super().__init__(
            f"field type '{field_type}' requires options of type '{expected}'"
        )


class FieldOptionsNotAllowedError(ValidationError):
    def __init__(self, field_type: str) -> None:
        super().__init__(f"field type '{field_type}' does not support options")


class FieldSettingsTypeMismatchError(ValidationError):
    def __init__(self, field_type: str, expected: str, got: str) -> None:
        super().__init__(
            f"field type '{field_type}' expects settings '{expected}', got '{got}'"
        )


class FieldDefaultTypeMismatchError(ValidationError):
    def __init__(self, field_type: str, expected: str, got: str) -> None:
        super().__init__(
            f"field type '{field_type}' expects default '{expected}', got '{got}'"
        )


class FieldRelationTargetRequiredError(ValidationError):
    def __init__(self) -> None:
        super().__init__("relation field requires relation_target_object_id")


class FieldRelationTargetNotAllowedError(ValidationError):
    def __init__(self, field_type: str) -> None:
        super().__init__(
            f"field type '{field_type}' must not define relation targets"
        )


class FieldOptionCodeRequiredError(ValidationError):
    def __init__(self) -> None:
        super().__init__("field option code is required")


class FieldOptionLabelRequiredError(ValidationError):
    def __init__(self) -> None:
        super().__init__("field option label is required")


class FieldOptionDuplicateCodeError(ValidationError):
    def __init__(self, code: str) -> None:
        super().__init__(f"field option code '{code}' is duplicated")


class FieldOptionSetCannotBeEmptyError(ValidationError):
    def __init__(self, option_type: str) -> None:
        super().__init__(f"{option_type} options must contain at least one item")


class FieldSettingBoundsError(ValidationError):
    def __init__(self, message: str) -> None:
        super().__init__(message)


class FieldDefaultOptionNotFoundError(ValidationError):
    def __init__(self, code: str) -> None:
        super().__init__(f"default option '{code}' is missing in options set")


class FieldDefaultRelationTargetMismatchError(ValidationError):
    def __init__(self) -> None:
        super().__init__(
            "relation default target must match relation_target_object_id/relation_target_field_id"
        )


class FieldDefaultExceedsMaxItemsError(ValidationError):
    def __init__(self, max_items: int, got: int) -> None:
        super().__init__(
            f"multi_select default contains {got} items, but max_items is {max_items}"
        )


class FieldTimestampOrderError(ValidationError):
    def __init__(self) -> None:
        super().__init__("updated_at must be greater or equal to created_at")


class FieldMaxItemsInvalidError(ValidationError):
    def __init__(self) -> None:
        super().__init__("max_items must be greater than zero")


class FieldDefaultValueInvalidError(ValidationError):
    def __init__(self, message: str) -> None:
        super().__init__(message)


class ObjectNameRequiredError(ValidationError):
    def __init__(self, field_name: str) -> None:
        super().__init__(f"object {field_name} is required")


class ObjectNameInvalidFormatError(ValidationError):
    def __init__(self, value: str) -> None:
        super().__init__(
            f"object name '{value}' has invalid format; expected snake_case"
        )


class ObjectLabelRequiredError(ValidationError):
    def __init__(self, field_name: str) -> None:
        super().__init__(f"object {field_name} label is required")


class ObjectTimestampOrderError(ValidationError):
    def __init__(self) -> None:
        super().__init__("object updated_at must be greater or equal to created_at")


class DataSourceTypeNotSupportedError(ValidationError):
    def __init__(self, value: str) -> None:
        super().__init__(f"data source type '{value}' is not supported")


class DataSourceSchemaRequiredError(ValidationError):
    def __init__(self) -> None:
        super().__init__("data source schema is required")


class DataSourceSchemaInvalidFormatError(ValidationError):
    def __init__(self, value: str) -> None:
        super().__init__(
            f"data source schema '{value}' has invalid format; expected [a-z_][a-z0-9_]* up to 63 chars"
        )


class DataSourceDsnInvalidError(ValidationError):
    def __init__(self, value: str) -> None:
        super().__init__(f"data source dsn '{value}' is invalid")


class DataSourceRemoteDsnRequiredError(ValidationError):
    def __init__(self) -> None:
        super().__init__("remote data source requires dsn")


class DataSourceTimestampOrderError(ValidationError):
    def __init__(self) -> None:
        super().__init__("data source updated_at must be greater or equal to created_at")


__all__ = [
    "DataSourceDsnInvalidError",
    "DataSourceRemoteDsnRequiredError",
    "DataSourceSchemaInvalidFormatError",
    "DataSourceSchemaRequiredError",
    "DataSourceTimestampOrderError",
    "DataSourceTypeNotSupportedError",
    "FieldDefaultExceedsMaxItemsError",
    "FieldDefaultOptionNotFoundError",
    "FieldDefaultRelationTargetMismatchError",
    "FieldDefaultTypeMismatchError",
    "FieldDefaultValueInvalidError",
    "FieldLabelRequiredError",
    "FieldMaxItemsInvalidError",
    "FieldNameInvalidFormatError",
    "FieldNameRequiredError",
    "FieldOptionCodeRequiredError",
    "FieldOptionDuplicateCodeError",
    "FieldOptionLabelRequiredError",
    "FieldOptionsNotAllowedError",
    "FieldOptionsRequiredError",
    "FieldOptionSetCannotBeEmptyError",
    "FieldRelationTargetNotAllowedError",
    "FieldRelationTargetRequiredError",
    "FieldSettingsTypeMismatchError",
    "FieldSettingBoundsError",
    "FieldTimestampOrderError",
    "FieldUniqueMustBeIndexedError",
    "ObjectLabelRequiredError",
    "ObjectNameInvalidFormatError",
    "ObjectNameRequiredError",
    "ObjectTimestampOrderError",
]
