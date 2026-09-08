"""Регистрация статических tenant-моделей и их исторических имён."""

import src.modules.inventory.infrastructure.persistence  # noqa: F401
import src.modules.identity.infrastructure.persistence  # noqa: F401

# Не удалять имена при удалении модели: autogenerate должен видеть DROP TABLE.
HISTORICAL_TENANT_TABLE_NAMES = frozenset({"warehouses", "users", "user_emails"})
