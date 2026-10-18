"""Rename the company name to legal_name without replacing stored values."""

from alembic import op

revision = "0010_crm_company_legal_name"
down_revision = "0009_crm_contact_companies"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("companies", "name", new_column_name="legal_name")
    op.execute(
        "ALTER TABLE companies RENAME CONSTRAINT ck_companies_name "
        "TO ck_companies_legal_name"
    )
    op.execute("ALTER INDEX ix_companies_name RENAME TO ix_companies_legal_name")


def downgrade() -> None:
    op.alter_column("companies", "legal_name", new_column_name="name")
    op.execute(
        "ALTER TABLE companies RENAME CONSTRAINT ck_companies_legal_name "
        "TO ck_companies_name"
    )
    op.execute("ALTER INDEX ix_companies_legal_name RENAME TO ix_companies_name")
