"""Create users and their email addresses inside each tenant schema."""

from alembic import op
import sqlalchemy as sa

revision = "0002_identity_users"
down_revision = "0001_warehouses"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Создает identity-таблицы в схеме, выбранной migration environment."""
    op.create_table(
        "users",
        sa.Column("id", sa.UUID(), nullable=False),
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
        sa.Column(
            "status", sa.String(255), server_default=sa.text("'active'"), nullable=False
        ),
        sa.Column("user_type", sa.String(255), nullable=False),
        sa.Column("last_name", sa.String(255), nullable=False),
        sa.Column("first_name", sa.String(255), nullable=False),
        sa.Column("middle_name", sa.String(255), nullable=True),
        sa.Column("avatar", sa.String(255), nullable=True),
        sa.Column(
            "interface_language", sa.String(255), server_default="uk", nullable=False
        ),
        sa.Column(
            "interface_theme", sa.String(255), server_default="system", nullable=False
        ),
        sa.Column(
            "timezone", sa.String(255), server_default="Europe/Kyiv", nullable=False
        ),
        sa.Column(
            "last_login_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=True,
        ),
        sa.Column("last_active_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_login_ip", sa.String(255), nullable=True),
        sa.Column("initialized_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_users"),
    )
    op.create_index("ix_users_status", "users", ["status"])
    op.create_table(
        "user_emails",
        sa.Column("id", sa.UUID(), nullable=False),
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
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column(
            "is_primary",
            sa.Boolean(),
            server_default=sa.text("'false'"),
            nullable=False,
        ),
        sa.Column(
            "is_verified",
            sa.Boolean(),
            server_default=sa.text("'false'"),
            nullable=False,
        ),
        sa.Column(
            "is_deleted",
            sa.Boolean(),
            server_default=sa.text("'false'"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_user_emails"),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name="fk_user_emails_user_id"
        ),
    )
    op.create_index("ix_user_emails_user_id", "user_emails", ["user_id"])


def downgrade() -> None:
    """Удаляет identity-таблицы текущего tenant, сохраняя остальные таблицы."""
    op.drop_index("ix_user_emails_user_id", table_name="user_emails")
    op.drop_table("user_emails")
    op.drop_index("ix_users_status", table_name="users")
    op.drop_table("users")
