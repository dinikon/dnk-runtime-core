"""Add tenant contact points, bindings and configurable labels."""

from datetime import UTC, datetime
from uuid import UUID

from alembic import op
import sqlalchemy as sa

revision = "0008_contact_points"
down_revision = "0007_crm_contacts_companies"
branch_labels = None
depends_on = None


def _audit_columns(*, nullable_actor=False):
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
        sa.Column("created_by", sa.UUID(), nullable=nullable_actor),
        sa.Column("updated_by", sa.UUID(), nullable=nullable_actor),
    )


def upgrade() -> None:
    """Создаёт справочник в выбранной tenant-схеме без отдельного commit."""
    op.create_table(
        "contact_points",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("type", sa.String(10), nullable=False),
        sa.Column("canonical_value", sa.String(320), nullable=False),
        sa.Column("country_code", sa.String(2)),
        *_audit_columns(),
        sa.UniqueConstraint("type", "canonical_value", name="uq_contact_points_value"),
        sa.CheckConstraint("type IN ('phone', 'email')", name="ck_contact_points_type"),
        sa.CheckConstraint(
            "char_length(btrim(canonical_value)) BETWEEN 1 AND 320",
            name="ck_contact_points_value",
        ),
        sa.CheckConstraint(
            "(type = 'phone' AND country_code IS NOT NULL AND char_length(country_code) = 2) OR (type = 'email' AND country_code IS NULL)",
            name="ck_contact_points_country",
        ),
    )
    labels = op.create_table(
        "contact_point_labels",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("type", sa.String(10), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        *_audit_columns(nullable_actor=True),
        sa.CheckConstraint(
            "type IN ('phone', 'email')", name="ck_contact_point_labels_type"
        ),
        sa.CheckConstraint(
            "char_length(btrim(name)) BETWEEN 1 AND 100",
            name="ck_contact_point_labels_name",
        ),
    )
    op.create_index(
        "ix_contact_point_labels_type", "contact_point_labels", ["type", "name", "id"]
    )
    op.create_table(
        "contact_point_bindings",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("contact_point_id", sa.UUID(), nullable=False),
        sa.Column("model_key", sa.String(100), nullable=False),
        sa.Column("record_id", sa.UUID(), nullable=False),
        sa.Column("label_id", sa.UUID()),
        sa.Column("position", sa.Integer(), nullable=False),
        *_audit_columns(),
        sa.ForeignKeyConstraint(
            ["contact_point_id"],
            ["contact_points.id"],
            name="fk_contact_point_bindings_point",
        ),
        sa.ForeignKeyConstraint(
            ["label_id"],
            ["contact_point_labels.id"],
            name="fk_contact_point_bindings_label",
        ),
        sa.UniqueConstraint(
            "model_key",
            "record_id",
            "contact_point_id",
            name="uq_contact_point_bindings_target_point",
        ),
        sa.CheckConstraint("position >= 0", name="ck_contact_point_bindings_position"),
    )
    op.create_index(
        "ix_contact_point_bindings_target",
        "contact_point_bindings",
        ["model_key", "record_id", "position", "id"],
    )
    op.create_index(
        "ix_contact_point_bindings_point",
        "contact_point_bindings",
        ["contact_point_id"],
    )
    op.create_index(
        "ix_contact_point_bindings_label", "contact_point_bindings", ["label_id"]
    )
    now = datetime(2026, 9, 24, tzinfo=UTC)
    op.bulk_insert(
        labels,
        [
            dict(
                id=UUID(f"01997b20-0000-7000-8000-{index:012d}"),
                type=kind,
                name=name,
                is_active=True,
                created_at=now,
                updated_at=now,
                created_by=None,
                updated_by=None,
            )
            for index, (kind, name) in enumerate(
                (
                    (kind, name)
                    for kind in ("phone", "email")
                    for name in ("Рабочий", "Личный", "Другой")
                ),
                start=1,
            )
        ],
    )


def downgrade() -> None:
    """Удаляет только таблицы contact_points в текущей схеме."""
    op.drop_table("contact_point_bindings")
    op.drop_table("contact_point_labels")
    op.drop_table("contact_points")
