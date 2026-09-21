from __future__ import annotations

from src.modules.currency.infrastructure.persistence.schema import code_check
import sqlalchemy as sa
from src.modules.shared.infrastructure.persistence import StringUUID
from src.modules.shared.infrastructure.persistence import TenantBase


class ResolutionFailureModel(TenantBase):
    """Durable tenant diagnostic, written with its outbox event."""

    __table__ = sa.Table(
        "currency_resolution_failure",
        TenantBase.metadata,
        sa.Column("id", StringUUID, primary_key=True),
        sa.Column("operation_id", StringUUID, nullable=False),
        sa.Column("source_currency", sa.String(3), nullable=False),
        sa.Column("target_currency", sa.String(3)),
        sa.Column("business_date", sa.Date, nullable=True),
        sa.Column("provider_code", sa.String(32)),
        sa.Column("policy_version", sa.Integer, nullable=False),
        sa.Column("error_code", sa.String(64), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deduplication_key", sa.String(64), nullable=False, unique=True),
        code_check("source_currency", "ck_currency_failure_source"),
        sa.CheckConstraint(
            "target_currency IS NULL OR target_currency ~ '^[A-Z]{3}$'",
            name="ck_currency_failure_target",
        ).ddl_if(dialect="postgresql"),
        sa.CheckConstraint(
            "policy_version >= 0", name="ck_currency_failure_policy_version"
        ),
        sa.Index("ix_currency_resolution_failure_operation", "operation_id"),
    )


__all__ = ["ResolutionFailureModel"]
