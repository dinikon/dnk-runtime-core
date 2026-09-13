"""Add local access roles, session revocation and explicit cloud identities."""

from alembic import op
import sqlalchemy as sa

revision = "0003_identity_cloud_access"
down_revision = "0002_identity_users"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "users",
        sa.Column("role", sa.String(16), nullable=False, server_default="member"),
    )
    op.add_column(
        "users",
        sa.Column("session_epoch", sa.BigInteger(), nullable=False, server_default="0"),
    )
    op.create_check_constraint("ck_users_role", "users", "role IN ('admin', 'member')")
    op.create_check_constraint("ck_users_session_epoch", "users", "session_epoch >= 0")
    # A collision is an explicit migration failure, never an implicit account merge.
    op.create_index(
        "uq_user_emails_live_email",
        "user_emails",
        ["email"],
        unique=True,
        postgresql_where=sa.text("NOT is_deleted"),
    )
    op.create_table(
        "cloud_identities",
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("issuer", sa.String(2048), nullable=False),
        sa.Column("subject", sa.String(255), nullable=False),
        sa.Column("linked_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("user_id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.UniqueConstraint("issuer", "subject", name="uq_cloud_identity_subject"),
    )
    op.create_table(
        "invitations",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("role", sa.String(16), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("state", sa.String(16), nullable=False),
        sa.Column("created_by", sa.UUID(), nullable=False),
        sa.Column("accepted_by", sa.UUID(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["accepted_by"], ["users.id"]),
        sa.CheckConstraint("role IN ('admin', 'member')", name="ck_invitations_role"),
        sa.CheckConstraint(
            "state IN ('pending', 'accepted', 'revoked')", name="ck_invitations_state"
        ),
    )


def downgrade():
    op.drop_table("invitations")
    op.drop_table("cloud_identities")
    op.drop_index("uq_user_emails_live_email", table_name="user_emails")
    op.drop_constraint("ck_users_session_epoch", "users", type_="check")
    op.drop_constraint("ck_users_role", "users", type_="check")
    op.drop_column("users", "session_epoch")
    op.drop_column("users", "role")
