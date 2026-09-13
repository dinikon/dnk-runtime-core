"""Public schema migrations only; caller supplies the transaction and lock."""

from alembic import context
from sqlalchemy import text

connection = context.config.attributes.get("connection")
if connection is None:
    raise RuntimeError("Use dnk-manage database upgrade to supply a transaction.")
connection.execute(text("SET LOCAL search_path TO public"))
context.configure(
    connection=connection,
    version_table="alembic_version_global",
    version_table_schema="public",
    transactional_ddl=True,
)
with context.begin_transaction():
    context.run_migrations()
