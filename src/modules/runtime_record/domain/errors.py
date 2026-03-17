from __future__ import annotations

from uuid import UUID

from src.modules.shared.domain.errors import DomainError


class RuntimeRecordValidationError(DomainError):
    def __init__(self, message: str):
        super().__init__(message)


class RuntimeObjectNotFoundError(DomainError):
    def __init__(self, *, tenant_id: UUID, object_name_singular: str):
        super().__init__(
            "Runtime object metadata was not found for "
            f"tenant_id='{tenant_id}', object='{object_name_singular}'."
        )


class RuntimeDataSourceNotFoundError(DomainError):
    def __init__(self, data_source_id: UUID):
        super().__init__(f"Runtime data source '{data_source_id}' was not found.")


class RuntimeRecordNotFoundError(DomainError):
    def __init__(self, *, table_name: str, record_id: UUID):
        super().__init__(
            f"Runtime record '{record_id}' was not found in table '{table_name}'."
        )


__all__ = [
    "RuntimeDataSourceNotFoundError",
    "RuntimeObjectNotFoundError",
    "RuntimeRecordNotFoundError",
    "RuntimeRecordValidationError",
]
