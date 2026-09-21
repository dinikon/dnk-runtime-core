from __future__ import annotations
import sqlalchemy as sa
from src.modules.shared.infrastructure.persistence import StringUUID


def timestamps():
    return [
        sa.Column(
            name,
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        )
        for name in ("created_at", "updated_at")
    ]


def code_check(column, name):
    return sa.CheckConstraint(f"{column} ~ '^[A-Z]{{3}}$'", name=name).ddl_if(
        dialect="postgresql"
    )


def rate_table(name, metadata, *, provider):
    keys = (["provider_code"] if provider else []) + [
        "source_currency",
        "target_currency",
        "effective_date",
    ]
    columns = [
        sa.Column("id", StringUUID, primary_key=True),
        sa.Column("source_currency", sa.String(3), nullable=False),
        sa.Column("target_currency", sa.String(3), nullable=False),
        sa.Column("rate", sa.Numeric(), nullable=False),
        sa.Column("effective_date", sa.Date, nullable=False),
        sa.Column("revision", sa.Integer, nullable=False),
        sa.Column("is_current", sa.Boolean, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    ]
    if provider:
        columns += [
            sa.Column("provider_code", sa.String(32), nullable=False),
            sa.Column("calculated_date", sa.Date),
            sa.Column("published_at", sa.DateTime(timezone=True)),
            sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("payload_hash", sa.String(64), nullable=False),
        ]
    else:
        columns += [sa.Column("created_by", StringUUID, nullable=False)]
    table = sa.Table(
        name,
        metadata,
        *columns,
        sa.UniqueConstraint(*keys, "revision", name=f"uq_{name}_revision"),
        sa.CheckConstraint(
            "rate > 0 AND rate < 'Infinity'", name=f"ck_{name}_positive"
        ),
        sa.CheckConstraint("revision > 0", name=f"ck_{name}_revision"),
        sa.CheckConstraint(
            "source_currency <> target_currency", name=f"ck_{name}_pair"
        ),
        code_check("source_currency", f"ck_{name}_source"),
        code_check("target_currency", f"ck_{name}_target"),
    )
    sa.Index(
        f"uq_{name}_current",
        *(table.c[k] for k in keys),
        unique=True,
        postgresql_where=table.c.is_current,
        sqlite_where=table.c.is_current,
    )
    sa.Index(
        f"ix_{name}_lookup",
        *(table.c[k] for k in keys[:-1]),
        table.c.effective_date.desc(),
        postgresql_where=table.c.is_current,
        sqlite_where=table.c.is_current,
    )
    return table


__all__ = ["code_check", "rate_table", "timestamps"]
