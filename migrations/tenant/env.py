"""Tenant-only Alembic environment; connections are supplied by TenantMigrator."""

from alembic import context
from sqlalchemy import text

from src.modules.shared.infrastructure.persistence.tenant_migration_metadata import (
    managed_table_names,
    migration_metadata,
    render_migration_item,
)

config = context.config
connection = config.attributes.get("connection")
if connection is None:
    raise RuntimeError(
        "Use dnk-manage tenant-migrations to supply a tenant and transaction."
    )

schema_name = config.attributes["tenant_schema"]
autogenerate = config.attributes.get("autogenerate", False)
metadata = migration_metadata(config.attributes.get("target_metadata"))
owned_tables = managed_table_names(metadata)


def include_name(name, kind, parent_names):
    if kind == "table":
        return name in owned_tables
    return True


original_path = connection.scalar(text("SHOW search_path"))
original_default = connection.dialect.default_schema_name
# set_config(..., true) is transaction-local SET LOCAL, with a bound value.
quoted_schema = connection.dialect.identifier_preparer.quote_schema(schema_name)
connection.execute(
    text("SELECT set_config('search_path', :path, true)"), {"path": quoted_schema}
)
try:
    if autogenerate:
        # Autogenerate alone uses a dedicated engine, never the application dialect.
        connection.dialect.default_schema_name = schema_name
    context.configure(
        connection=connection,
        target_metadata=metadata,
        version_table_schema=schema_name,
        include_schemas=False,
        include_name=include_name,
        compare_type=True,
        compare_server_default=True,
        render_item=render_migration_item,
        transactional_ddl=True,
    )
    with context.begin_transaction():
        context.run_migrations()
    connection.execute(
        text("SELECT set_config('search_path', :path, true)"), {"path": original_path}
    )
finally:
    # An aborted transaction is rolled back by the caller; don't mask its error.
    if autogenerate:
        connection.dialect.default_schema_name = original_default
