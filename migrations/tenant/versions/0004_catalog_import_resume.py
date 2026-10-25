"""Поколение исполнения для безопасного продолжения импортов.

Revision ID: 0004_catalog_import_resume
Revises: 0003_catalog_imports
"""

from alembic import op
import sqlalchemy as sa

revision = "0004_catalog_import_resume"
down_revision = "0003_catalog_imports"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Добавляет поколение без изменения сохранённых результатов и очереди."""
    op.add_column(
        "catalog_imports",
        sa.Column("generation", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_check_constraint(
        "ck_catalog_import_generation", "catalog_imports", "generation >= 0"
    )


def downgrade() -> None:
    """Удаляет метаданные продолжения, сохраняя существующие импорты."""
    op.drop_constraint("ck_catalog_import_generation", "catalog_imports", type_="check")
    op.drop_column("catalog_imports", "generation")
