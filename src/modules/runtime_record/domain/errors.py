from __future__ import annotations

from src.modules.shared.domain.errors import ValidationError


class RuntimeRecordDataSourceNotFoundError(ValidationError):
    def __init__(self, tenant_id: str):
        super().__init__(f"Primary data source for tenant '{tenant_id}' was not found.")


class RuntimeRecordObjectNotFoundError(ValidationError):
    def __init__(self, object_name_singular: str):
        super().__init__(f"Object '{object_name_singular}' was not found in runtime schema.")


class RuntimeRecordFieldNotFoundError(ValidationError):
    def __init__(self, *, object_name_singular: str, field_name: str):
        super().__init__(
            f"Field '{field_name}' was not found for object '{object_name_singular}'."
        )
