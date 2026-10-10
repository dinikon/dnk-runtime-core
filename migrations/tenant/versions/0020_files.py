"""Реестр системных хранилищ, приватных бакетов и файлов tenant."""

from alembic import op
import sqlalchemy as sa

revision = "0020_files"
down_revision = "0019_catalog_classification"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Создаёт только SQL-структуры, не обращаясь к MinIO."""
    op.create_table(
        "files_providers",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("kind", sa.String(64), nullable=False),
        sa.Column("is_system", sa.Boolean(), nullable=False),
        sa.Column("config_ref", sa.String(200), nullable=False),
        sa.CheckConstraint(
            "NOT is_system OR (kind = 'minio' AND config_ref = 'system_minio')",
            name="ck_files_system_config",
        ),
    )
    op.create_index(
        "uq_files_system_provider",
        "files_providers",
        ["is_system"],
        unique=True,
        postgresql_where=sa.text("is_system"),
    )
    op.create_table(
        "files_buckets",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "provider_id",
            sa.Uuid(),
            sa.ForeignKey("files_providers.id"),
            nullable=False,
        ),
        sa.Column("name", sa.String(63), nullable=False, unique=True),
        sa.Column("status", sa.String(20), nullable=False),
        sa.UniqueConstraint("provider_id", name="uq_files_provider_bucket"),
        sa.CheckConstraint(
            "status IN ('preparing', 'ready', 'purged')", name="ck_files_bucket_status"
        ),
    )
    op.create_table(
        "files_registry",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "bucket_id", sa.Uuid(), sa.ForeignKey("files_buckets.id"), nullable=False
        ),
        sa.Column("object_key", sa.String(32), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("content_type", sa.String(255), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("bucket_id", "object_key", name="uq_files_object"),
        sa.CheckConstraint("size_bytes >= 0", name="ck_files_size"),
        sa.CheckConstraint("status IN ('uploading', 'ready')", name="ck_files_status"),
    )
    op.create_index("ix_files_bucket_status", "files_registry", ["bucket_id", "status"])


def downgrade() -> None:
    """Удаляет SQL-реестр; физические бакеты требуют предварительного purge."""
    op.drop_table("files_registry")
    op.drop_table("files_buckets")
    op.drop_table("files_providers")
