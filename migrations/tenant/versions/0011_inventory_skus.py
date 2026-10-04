"""Add independent inventory SKU identities to each tenant schema."""

from alembic import op
import sqlalchemy as sa

revision = "0011_inventory_skus"
down_revision = "0010_crm_company_legal_name"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Создаёт справочник SKU без складских остатков и отдельного commit."""
    op.create_table(
        "skus",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("code", sa.String(128), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("created_by", sa.UUID(), nullable=False),
        sa.Column("updated_by", sa.UUID(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_skus"),
        sa.UniqueConstraint("code", name="uq_skus_code"),
        sa.CheckConstraint(
            "char_length(code) BETWEEN 1 AND 128 AND code = btrim(code) "
            "AND code !~ '[[:cntrl:]]'",
            name="ck_skus_code",
        ),
        sa.CheckConstraint(
            "char_length(btrim(title)) BETWEEN 1 AND 255", name="ck_skus_title"
        ),
    )


def downgrade() -> None:
    """Удаляет только справочник SKU в текущей tenant-схеме."""
    op.drop_table("skus")
