"""Create static CRM contacts and companies."""

from alembic import op
import sqlalchemy as sa

revision = "0007_crm_contacts_companies"
down_revision = "0006_price_list_streaming"
branch_labels = None
depends_on = None


def _audit_columns():
    return (
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
    )


def upgrade() -> None:
    """Создаёт независимые CRM-таблицы в выбранной tenant-схеме."""
    op.create_table(
        "contacts",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("first_name", sa.String(255), nullable=False),
        sa.Column("last_name", sa.String(255), nullable=True),
        sa.Column("middle_name", sa.String(255), nullable=True),
        *_audit_columns(),
        sa.PrimaryKeyConstraint("id", name="pk_contacts"),
        sa.CheckConstraint(
            "char_length(btrim(first_name)) BETWEEN 1 AND 255",
            name="ck_contacts_first_name",
        ),
        sa.CheckConstraint(
            "last_name IS NULL OR char_length(btrim(last_name)) BETWEEN 1 AND 255",
            name="ck_contacts_last_name",
        ),
        sa.CheckConstraint(
            "middle_name IS NULL OR char_length(btrim(middle_name)) BETWEEN 1 AND 255",
            name="ck_contacts_middle_name",
        ),
    )
    op.create_index(
        "ix_contacts_name",
        "contacts",
        ["last_name", "first_name", "middle_name", "id"],
    )
    op.create_table(
        "companies",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        *_audit_columns(),
        sa.PrimaryKeyConstraint("id", name="pk_companies"),
        sa.CheckConstraint(
            "char_length(btrim(name)) BETWEEN 1 AND 255",
            name="ck_companies_name",
        ),
    )
    op.create_index("ix_companies_name", "companies", ["name", "id"])


def downgrade() -> None:
    """Удаляет только статические CRM-таблицы."""
    op.drop_index("ix_companies_name", table_name="companies")
    op.drop_table("companies")
    op.drop_index("ix_contacts_name", table_name="contacts")
    op.drop_table("contacts")
