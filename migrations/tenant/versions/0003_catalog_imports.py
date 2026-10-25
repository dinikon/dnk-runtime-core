"""Потоковый импорт Catalog, staging и идемпотентность медиа."""

from alembic import op

revision = "0003_catalog_imports"
down_revision = "0002_crm_sales_mvp"
branch_labels = None
depends_on = None

DDL = (
    "\nCREATE TABLE catalog_imports (\n\tid UUID NOT NULL, \n\tactor_id UUID NOT NULL, \n\tidempotency_key VARCHAR(200) NOT NULL, \n\tfingerprint VARCHAR(64) NOT NULL, \n\tsource_name VARCHAR(255) NOT NULL, \n\tsource_url TEXT, \n\tsource_file_id UUID, \n\tconfiguration JSONB NOT NULL, \n\tanalysis JSONB DEFAULT '{}' NOT NULL, \n\tstatus VARCHAR(32) NOT NULL, \n\tversion INTEGER NOT NULL, \n\tprepared_version INTEGER NOT NULL, \n\ttotal INTEGER NOT NULL, \n\tprocessed INTEGER NOT NULL, \n\tcreated INTEGER NOT NULL, \n\tupdated INTEGER NOT NULL, \n\tskipped INTEGER NOT NULL, \n\terrors INTEGER NOT NULL, \n\twarnings INTEGER NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tupdated_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tfinished_at TIMESTAMP WITH TIME ZONE, \n\tjob_id UUID, \n\terror VARCHAR(1000), \n\tPRIMARY KEY (id), \n\tUNIQUE (idempotency_key), \n\tCONSTRAINT ck_catalog_import_counts CHECK (total>=0 AND processed>=0 AND processed<=total AND created>=0 AND updated>=0 AND skipped>=0 AND errors>=0 AND warnings>=0 AND processed=created+updated+skipped+errors), \n\tCONSTRAINT ck_catalog_import_status CHECK (status IN ('preparing','mapping','queued','running','cancelling','cancelled','completed','completed_with_errors','failed','expired'))\n)\n\n",
    "CREATE INDEX ix_catalog_import_created ON catalog_imports (created_at, id)",
    "CREATE UNIQUE INDEX uq_catalog_import_executing ON catalog_imports ((true)) WHERE status IN ('queued','running','cancelling')",
    "\nCREATE TABLE catalog_import_rows (\n\tid UUID NOT NULL, \n\timport_id UUID NOT NULL, \n\tnumber INTEGER NOT NULL, \n\tvalues JSONB NOT NULL, \n\toutcome VARCHAR(16) NOT NULL, \n\tsku VARCHAR(255), \n\titem_id UUID, \n\terrors JSONB NOT NULL, \n\twarnings JSONB NOT NULL, \n\tPRIMARY KEY (id), \n\tFOREIGN KEY(import_id) REFERENCES catalog_imports (id) ON DELETE CASCADE, \n\tCONSTRAINT ck_catalog_import_row CHECK (number>0 AND outcome IN ('pending','created','updated','skipped','errors')), \n\tCONSTRAINT uq_catalog_import_row_number UNIQUE (import_id, number)\n)\n\n",
    "CREATE INDEX ix_catalog_import_row_pending ON catalog_import_rows (import_id, outcome, number)",
    "CREATE INDEX ix_catalog_import_row_sku ON catalog_import_rows (import_id, sku, number)",
    "\nCREATE TABLE catalog_import_media (\n\tid UUID NOT NULL, \n\timport_id UUID NOT NULL, \n\turl_hash VARCHAR(64) NOT NULL, \n\tfile_id UUID, \n\terror VARCHAR(500), \n\tPRIMARY KEY (id), \n\tCONSTRAINT uq_catalog_import_media_url UNIQUE (import_id, url_hash), \n\tFOREIGN KEY(import_id) REFERENCES catalog_imports (id) ON DELETE CASCADE\n)\n\n",
)


def upgrade() -> None:
    """Создаёт только новые таблицы импорта."""
    for statement in DDL:
        op.execute(statement)


def downgrade() -> None:
    """Удаляет таблицы импорта в обратном порядке зависимостей."""
    for name in ("catalog_import_media", "catalog_import_rows", "catalog_imports"):
        op.drop_table(name)
