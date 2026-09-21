from __future__ import annotations
import sqlalchemy as sa
from src.modules.shared.infrastructure.persistence import Base
from src.modules.shared.infrastructure.persistence import StringUUID


class RateImportModel(Base):
    """Persistence mapping for rate import."""

    __table__ = sa.Table(
        "fx_rate_import",
        Base.metadata,
        sa.Column("id", StringUUID, primary_key=True),
        sa.Column("provider_code", sa.String(32), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.Column("requested_date_from", sa.Date, nullable=False),
        sa.Column("requested_date_to", sa.Date, nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        *(
            sa.Column(n, sa.Integer, nullable=False, server_default="0")
            for n in ("received_count", "created_count", "updated_count", "error_count")
        ),
        sa.Column("error_message", sa.String(1000)),
        sa.CheckConstraint(
            "status IN ('running','succeeded','failed')", name="ck_fx_import_status"
        ),
        sa.Index("ix_fx_import_provider_started", "provider_code", "started_at"),
    )


__all__ = ["RateImportModel"]
