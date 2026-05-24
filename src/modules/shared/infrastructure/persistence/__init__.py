from __future__ import annotations

from importlib import import_module
from typing import Any

from src.modules.shared.infrastructure.persistence.audience_mixin import AudienceMixin
from src.modules.shared.infrastructure.persistence.base import Base, TENANT_SCHEMA_ALIAS
from src.modules.shared.infrastructure.persistence.database_startup_error import (
    DatabaseStartupError,
)
from src.modules.shared.infrastructure.persistence.long_text import LongText
from src.modules.shared.infrastructure.persistence.portable_json import PortableJSON
from src.modules.shared.infrastructure.persistence.string_uuid import StringUUID
from src.modules.shared.infrastructure.persistence.tenant_base import TenantBase
from src.modules.shared.infrastructure.persistence.tenant_system_mixin import (
    TenantSystemMixin,
)
from src.modules.shared.infrastructure.persistence.unit_of_work import UnitOfWork

_LAZY_EXPORTS: dict[str, str] = {
    "DatabaseHelper": "src.modules.shared.infrastructure.persistence.database_helper",
    "db_helper": "src.modules.shared.infrastructure.persistence.database_helper",
}

__all__ = [
    "AudienceMixin",
    "Base",
    "DatabaseHelper",
    "DatabaseStartupError",
    "LongText",
    "PortableJSON",
    "StringUUID",
    "TENANT_SCHEMA_ALIAS",
    "TenantBase",
    "TenantSystemMixin",
    "UnitOfWork",
    "db_helper",
]


def __getattr__(name: str) -> Any:
    """Лениво импортирует DB helper exports, чтобы не создавать engine при импорте моделей."""

    module_path = _LAZY_EXPORTS.get(name)
    if module_path is None:
        raise AttributeError(
            f"module {__name__!r} has no attribute {name!r}",
        )
    module = import_module(module_path)
    return getattr(module, name)
