"""Переносит observed-снимок в payload/meta без изменения identity и связей."""

from collections.abc import Iterator, Mapping
from datetime import datetime, timezone
from decimal import Decimal
from hashlib import sha256
import json
from typing import Any
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "0032_publication_payload_meta"
down_revision = "0031_channel_content_updates"
branch_labels = None
depends_on = None

TABLE = "channel_external_publications"
LEGACY = (
    ("external_sku", sa.String(512)),
    ("price", sa.Numeric(30, 12)),
    ("sale_price", sa.Numeric(30, 12)),
    ("currency", sa.String(3)),
    ("quantity", sa.Numeric(30, 12)),
    ("stock_status", sa.String(30)),
    ("title", sa.String(2000)),
    ("title_locale", sa.String(100)),
    ("main_image_url", sa.String(4096)),
    ("warnings", JSONB()),
    ("extension_version", sa.String(100)),
    ("extensions", JSONB()),
)


def _rows() -> Iterator[Mapping[str, Any]]:
    """Читает ограниченные порции в стабильном порядке без загрузки всей таблицы."""
    cursor = None
    while True:
        statement = f"SELECT * FROM {TABLE}"
        if cursor is not None:
            statement += " WHERE id > :cursor"
        rows = (
            op.get_bind()
            .execute(sa.text(statement + " ORDER BY id LIMIT 500"), {"cursor": cursor})
            .mappings()
            .all()
        )
        if not rows:
            return
        yield from rows
        cursor = rows[-1]["id"]


def _decimal(value: Decimal | None) -> str | None:
    """Фиксирует строковый формат чисел версии payload 1 без округления."""
    if value is None:
        return None
    result = format(value, "f")
    if "." in result:
        result = result.rstrip("0").rstrip(".")
    return "0" if result in ("-0", "") else result


def _promotion(provider: dict[str, Any], schema: str) -> dict[str, Any] | None:
    """Переносит известные периоды v1, сохраняя исходные значения в provider."""
    try:
        if schema.startswith("prom."):
            discount = provider.get("discount") or {}
            dates = tuple(
                (
                    datetime.strptime(discount[key], "%d.%m.%Y").date().isoformat()
                    if discount.get(key)
                    else None
                )
                for key in ("date_start", "date_end")
            )
            zone, precision = "Europe/Kyiv", "day"
        elif schema.startswith("woocommerce."):
            dates = tuple(
                (
                    datetime.fromisoformat(provider[key])
                    .replace(tzinfo=timezone.utc)
                    .isoformat()
                    if provider.get(key)
                    else None
                )
                for key in ("sale_start_gmt", "sale_end_gmt")
            )
            zone, precision = "UTC", "instant"
        else:
            return None
    except (ValueError, TypeError, KeyError):
        return None
    if not any(dates) or (all(dates) and dates[0] > dates[1]):
        return None
    return {
        "starts_at": dates[0],
        "ends_at": dates[1],
        "timezone": zone,
        "precision": precision,
    }


def _snapshot(row: Mapping[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    """Закрепляет преобразование исторических v1-схем без импорта рабочего кода."""
    provider = dict(row["extensions"])
    retained = provider.pop("_channels_payload_v1", {})
    schema = row["extension_version"]
    if schema == "prom.read.v1":
        provider["import_key"] = provider.pop("provider_external_id", None)
        schema = "prom.read.v2"
    elif schema == "woocommerce.read.v1":
        schema = "woocommerce.read.v2"
    titles = dict(retained.get("titles", {}))
    locale = row["title_locale"] or "und"
    if row["title"] is not None:
        titles[locale] = row["title"]
    else:
        titles.pop(locale, None)
    payload = {
        "schema_version": 1,
        "sku": row["external_sku"],
        "titles": titles,
        "display_locale": row["title_locale"],
        "pricing": {
            "regular": _decimal(row["price"]),
            "sale": _decimal(row["sale_price"]),
            "currency": row["currency"],
            "promotion": _promotion(provider, schema),
        },
        "stock": {"quantity": _decimal(row["quantity"]), "status": row["stock_status"]},
        "main_image": (
            {"url": row["main_image_url"]}
            if row["main_image_url"] is not None
            else None
        ),
    }
    meta = {
        "schema_version": 1,
        "provider_schema": schema,
        "provider": provider,
        "read_issues": row["warnings"],
    }
    return payload, meta


def upgrade() -> None:
    """Переносит данные на месте, сохраняя UUID, FK и observed_revision."""
    op.add_column(TABLE, sa.Column("payload", JSONB(), nullable=True))
    op.add_column(TABLE, sa.Column("meta", JSONB(), nullable=True))
    for row in _rows():
        payload, meta = _snapshot(row)
        source = row["source_updated_at"]
        fingerprint = sha256(
            json.dumps(
                {
                    "payload": payload,
                    "meta": meta,
                    "source_updated_at": (
                        source.astimezone(timezone.utc).isoformat()
                        if source is not None
                        else None
                    ),
                },
                sort_keys=True,
                ensure_ascii=False,
                allow_nan=False,
            ).encode()
        ).hexdigest()
        op.get_bind().execute(
            sa.text(
                f"UPDATE {TABLE} SET payload=CAST(:payload AS jsonb), "
                "meta=CAST(:meta AS jsonb), fingerprint=:fingerprint WHERE id=:id"
            ),
            {
                "id": row["id"],
                "payload": json.dumps(payload, ensure_ascii=False),
                "meta": json.dumps(meta, ensure_ascii=False),
                "fingerprint": fingerprint,
            },
        )
    op.alter_column(TABLE, "payload", nullable=False)
    op.alter_column(TABLE, "meta", nullable=False)
    op.drop_index("ix_channel_publications_sku", table_name=TABLE)
    op.drop_index("ix_channel_publications_stock", table_name=TABLE)
    for name, _ in LEGACY:
        op.drop_column(TABLE, name)
    op.create_index(
        "ix_channel_publications_sku",
        TABLE,
        ["connection_id", sa.text("(payload ->> 'sku')")],
    )
    op.create_index(
        "ix_channel_publications_stock",
        TABLE,
        ["connection_id", sa.text("((payload -> 'stock') ->> 'status')")],
    )


def downgrade() -> None:
    """Восстанавливает старую схему; дополнительные локали переживают откат в extensions."""
    op.drop_index("ix_channel_publications_sku", table_name=TABLE)
    op.drop_index("ix_channel_publications_stock", table_name=TABLE)
    for name, column_type in LEGACY:
        op.add_column(TABLE, sa.Column(name, column_type, nullable=True))
    table = sa.table(
        TABLE,
        *(sa.column(name, column_type) for name, column_type in LEGACY),
        sa.column("id", sa.UUID()),
        sa.column("fingerprint", sa.String(64)),
    )
    for row in _rows():
        payload, meta = row["payload"], row["meta"]
        pricing, stock = payload["pricing"], payload["stock"]
        image = payload["main_image"]
        core = {
            "resource_type": row["resource_type"],
            "external_id": row["external_id"],
            "external_sku": payload["sku"],
            "price": (
                Decimal(pricing["regular"]) if pricing["regular"] is not None else None
            ),
            "sale_price": (
                Decimal(pricing["sale"]) if pricing["sale"] is not None else None
            ),
            "currency": pricing["currency"],
            "quantity": (
                Decimal(stock["quantity"]) if stock["quantity"] is not None else None
            ),
            "stock_status": stock["status"],
            "title": payload["titles"].get(payload["display_locale"] or "und"),
            "title_locale": payload["display_locale"],
            "main_image_url": image["url"] if image is not None else None,
            "warnings": meta["read_issues"],
            "source_updated_at": row["source_updated_at"],
        }
        schema = meta["provider_schema"]
        provider = dict(meta["provider"])
        if schema == "prom.read.v2":
            provider["provider_external_id"] = provider.pop("import_key", None)
            schema = "prom.read.v1"
        elif schema == "woocommerce.read.v2":
            schema = "woocommerce.read.v1"
        provider["_channels_payload_v1"] = payload
        fingerprint = sha256(
            json.dumps(
                {"core": core, "version": schema, "extensions": provider},
                sort_keys=True,
                default=str,
                ensure_ascii=False,
            ).encode()
        ).hexdigest()
        values = {name: core[name] for name, _ in LEGACY if name in core}
        values.update(
            extension_version=schema, extensions=provider, fingerprint=fingerprint
        )
        op.get_bind().execute(
            table.update().where(table.c.id == row["id"]).values(**values)
        )
    for name in ("stock_status", "warnings", "extension_version", "extensions"):
        op.alter_column(TABLE, name, nullable=False)
    op.drop_column(TABLE, "payload")
    op.drop_column(TABLE, "meta")
    op.create_index(
        "ix_channel_publications_sku", TABLE, ["connection_id", "external_sku"]
    )
    op.create_index(
        "ix_channel_publications_stock", TABLE, ["connection_id", "stock_status"]
    )
