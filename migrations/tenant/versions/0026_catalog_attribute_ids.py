"""Удаление кодов атрибутов и опций с сохранением UUID, переводов и связей."""

from alembic import op
import sqlalchemy as sa

revision = "0026_catalog_attribute_ids"
down_revision = "0025_user_display_currency"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Удаляет только коды и их уникальность в текущей tenant-схеме."""
    op.drop_constraint(
        "uq_catalog_option_code", "catalog_attribute_options", type_="unique"
    )
    op.drop_column("catalog_attribute_options", "code")
    op.drop_constraint(
        "catalog_attributes_code_key", "catalog_attributes", type_="unique"
    )
    op.drop_column("catalog_attributes", "code")


def downgrade() -> None:
    """Восстанавливает служебные коды из UUID; прежние значения требуют бэкапа."""
    op.add_column("catalog_attributes", sa.Column("code", sa.String(64), nullable=True))
    op.add_column(
        "catalog_attribute_options", sa.Column("code", sa.String(64), nullable=True)
    )
    op.execute(
        "UPDATE catalog_attributes SET code = 'a_' || replace(id::text, '-', '')"
    )
    op.execute(
        "UPDATE catalog_attribute_options SET code = 'o_' || replace(id::text, '-', '')"
    )
    op.alter_column("catalog_attributes", "code", nullable=False)
    op.alter_column("catalog_attribute_options", "code", nullable=False)
    op.create_unique_constraint(
        "catalog_attributes_code_key", "catalog_attributes", ["code"]
    )
    op.create_unique_constraint(
        "uq_catalog_option_code", "catalog_attribute_options", ["attribute_id", "code"]
    )
