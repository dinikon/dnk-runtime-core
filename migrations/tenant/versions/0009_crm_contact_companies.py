"""Add company membership owned by CRM contacts."""

from alembic import op
import sqlalchemy as sa

revision = "0009_crm_contact_companies"
down_revision = "0008_contact_points"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "contact_companies",
        sa.Column("contact_id", sa.UUID(), primary_key=True),
        sa.Column("company_id", sa.UUID(), primary_key=True),
        sa.ForeignKeyConstraint(
            ["contact_id"],
            ["contacts.id"],
            name="fk_contact_companies_contact",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["company_id"],
            ["companies.id"],
            name="fk_contact_companies_company",
            ondelete="CASCADE",
        ),
    )
    op.create_index(
        "ix_contact_companies_company",
        "contact_companies",
        ["company_id", "contact_id"],
    )


def downgrade() -> None:
    op.drop_table("contact_companies")
