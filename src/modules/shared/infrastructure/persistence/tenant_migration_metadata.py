from sqlalchemy import MetaData
from sqlalchemy.schema import BLANK_SCHEMA

from src.modules.shared.infrastructure.persistence.base import TENANT_SCHEMA_ALIAS
from src.modules.shared.infrastructure.persistence.string_uuid import StringUUID
from src.modules.shared.infrastructure.persistence.tenant_base import TenantBase


def migration_metadata(source: MetaData | None = None) -> MetaData:
    """Копирует tenant metadata без схем, сохраняя внутренние FK."""
    import src.modules.tenant_persistence  # noqa: F401

    copied = MetaData()
    for table in (TenantBase.metadata if source is None else source).sorted_tables:
        table.to_metadata(
            copied,
            schema=None,
            referred_schema_fn=lambda table, schema, constraint, referred: (
                BLANK_SCHEMA if referred == TENANT_SCHEMA_ALIAS else referred
            ),
        )
    return copied


def managed_table_names(metadata: MetaData) -> frozenset[str]:
    """Возвращает текущие и исторические имена статических таблиц."""
    from src.modules.tenant_persistence import HISTORICAL_TENANT_TABLE_NAMES

    return HISTORICAL_TENANT_TABLE_NAMES | frozenset(metadata.tables)


def render_migration_item(kind, item, autogen_context):
    """Сохраняет ревизии независимыми от runtime UUID TypeDecorator."""
    if kind == "type" and isinstance(item, StringUUID):
        return "sa.UUID()"
    return False
