from __future__ import annotations

from src.modules.shared.domain.errors import ValidationError


class CustomObjectNameRequiredError(ValidationError):
    def __init__(self):
        super().__init__("custom object name is required")


class CustomObjectNameInvalidError(ValidationError):
    def __init__(self, value: str):
        super().__init__(f"custom object name '{value}' has invalid format")


class CustomObjectNotFoundError(ValidationError):
    def __init__(self, object_name_singular: str):
        super().__init__(f"custom object '{object_name_singular}' was not found")


class CustomObjectRecordNotFoundError(ValidationError):
    def __init__(self, object_name_singular: str, record_id: str):
        super().__init__(
            f"record '{record_id}' for custom object '{object_name_singular}' was not found"
        )


class CustomObjectDataSourceNotFoundError(ValidationError):
    def __init__(self, tenant_id: str):
        super().__init__(f"primary data source for tenant '{tenant_id}' was not found")


class CustomObjectRelationTargetRequiredError(ValidationError):
    def __init__(self, field_name: str):
        super().__init__(
            f"relation field '{field_name}' requires relation target object name"
        )


class CustomObjectRelationTargetNotFoundError(ValidationError):
    def __init__(self, target_object_name: str):
        super().__init__(
            f"relation target object '{target_object_name}' was not found"
        )


__all__ = [
    "CustomObjectDataSourceNotFoundError",
    "CustomObjectNameInvalidError",
    "CustomObjectNameRequiredError",
    "CustomObjectNotFoundError",
    "CustomObjectRecordNotFoundError",
    "CustomObjectRelationTargetNotFoundError",
    "CustomObjectRelationTargetRequiredError",
]
