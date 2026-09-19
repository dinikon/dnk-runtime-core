from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from src.modules.shared.infrastructure.persistence import (
    LongText,
    PortableJSON,
    StringUUID,
    TenantBase,
    TenantSystemMixin,
)
from src.modules.shared.infrastructure.persistence.base import TENANT_SCHEMA_ALIAS


class PriceListModel(TenantSystemMixin, TenantBase):
    __tablename__ = "price_lists"
    __table_args__ = (
        sa.CheckConstraint(
            "status IN ('draft','ready','active','paused','invalid')",
            name="ck_price_lists_status",
        ),
        sa.CheckConstraint(
            "source_format IN ('xml','yaml','xlsx')",
            name="ck_price_lists_source_format",
        ),
        sa.CheckConstraint(
            "new_item_policy IN ('create','quarantine','ignore')",
            name="ck_price_lists_new_policy",
        ),
        sa.CheckConstraint(
            "missing_item_policy IN "
            "('mark_out_of_stock','mark_missing','keep_last','archive')",
            name="ck_price_lists_missing_policy",
        ),
        sa.CheckConstraint("missing_threshold >= 1", name="ck_price_lists_threshold"),
        sa.Index("ix_price_lists_status_next_sync", "status", "next_sync_at"),
    )

    status: Mapped[str] = mapped_column(sa.String(16), default="draft")
    source_format: Mapped[str] = mapped_column(sa.String(16), nullable=False)
    source_preset: Mapped[str | None] = mapped_column(sa.String(64))
    source_url_secret: Mapped[str] = mapped_column(LongText, nullable=False)
    source_url_display: Mapped[str] = mapped_column(sa.String(2048), nullable=False)
    source_config: Mapped[dict[str, Any]] = mapped_column(
        PortableJSON, default=dict, nullable=False
    )
    mapping_config: Mapped[dict[str, Any]] = mapped_column(
        PortableJSON, default=dict, nullable=False
    )
    mapping_version: Mapped[int] = mapped_column(sa.Integer, default=1)
    cron_expression: Mapped[str | None] = mapped_column(sa.String(128))
    timezone: Mapped[str] = mapped_column(sa.String(64), default="Europe/Kyiv")
    new_item_policy: Mapped[str] = mapped_column(sa.String(32), default="create")
    missing_item_policy: Mapped[str] = mapped_column(
        sa.String(32), default="mark_out_of_stock"
    )
    missing_threshold: Mapped[int] = mapped_column(sa.Integer, default=2)
    schedule_revision: Mapped[int] = mapped_column(sa.Integer, default=1)
    next_sync_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True))
    last_sync_run_id: Mapped[UUID | None] = mapped_column(
        StringUUID,
        sa.ForeignKey(
            f"{TENANT_SCHEMA_ALIAS}.price_list_sync_runs.id",
            ondelete="SET NULL",
            use_alter=True,
            name="fk_price_lists_last_sync_run",
        ),
    )
    last_success_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True))
    last_error_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True))


class PartnerOfferModel(TenantSystemMixin, TenantBase):
    __tablename__ = "partner_offers"
    __table_args__ = (
        sa.UniqueConstraint(
            "price_list_id", "external_id", name="uq_partner_offer_external_id"
        ),
        sa.Index("ix_partner_offers_price_list", "price_list_id"),
        sa.Index("ix_partner_offers_search", "title", "sku", "external_id"),
    )

    price_list_id: Mapped[UUID] = mapped_column(
        StringUUID,
        sa.ForeignKey(
            f"{TENANT_SCHEMA_ALIAS}.price_lists.id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )
    sku: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    external_id: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    lifecycle_status: Mapped[str] = mapped_column(sa.String(16), default="active")
    current_state_id: Mapped[UUID | None] = mapped_column(
        StringUUID,
        sa.ForeignKey(
            f"{TENANT_SCHEMA_ALIAS}.partner_offer_states.id",
            ondelete="SET NULL",
            use_alter=True,
            name="fk_partner_offers_current_state",
        ),
    )
    first_seen_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True))
    last_seen_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True))
    missing_since: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True))
    consecutive_missing_runs: Mapped[int] = mapped_column(sa.Integer, default=0)


class PriceListSyncRunModel(TenantBase):
    __tablename__ = "price_list_sync_runs"
    __table_args__ = (
        sa.UniqueConstraint(
            "price_list_id", "scheduled_job_id", name="uq_price_list_run_job"
        ),
        sa.Index("ix_price_list_runs_list_started", "price_list_id", "started_at"),
        sa.CheckConstraint(
            "status IN ('queued','downloading','parsing','applying',"
            "'succeeded','partial','failed','skipped')",
            name="ck_price_list_runs_status",
        ),
        sa.CheckConstraint(
            "trigger IN ('initial','cron','manual','retry')",
            name="ck_price_list_runs_trigger",
        ),
    )

    id: Mapped[UUID] = mapped_column(StringUUID, primary_key=True)
    price_list_id: Mapped[UUID] = mapped_column(
        StringUUID,
        sa.ForeignKey(f"{TENANT_SCHEMA_ALIAS}.price_lists.id", ondelete="CASCADE"),
    )
    scheduled_job_id: Mapped[UUID | None] = mapped_column(StringUUID)
    status: Mapped[str] = mapped_column(sa.String(16), nullable=False)
    trigger: Mapped[str] = mapped_column(sa.String(16), nullable=False)
    planned_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True))
    started_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True))
    source_checksum: Mapped[str | None] = mapped_column(sa.String(64))
    counters: Mapped[dict[str, Any]] = mapped_column(
        PortableJSON, default=dict, nullable=False
    )
    error_summary: Mapped[str | None] = mapped_column(LongText)


class PartnerOfferStateModel(TenantBase):
    __tablename__ = "partner_offer_states"
    __table_args__ = (
        sa.CheckConstraint("purchase_price >= 0", name="ck_offer_state_price"),
        sa.CheckConstraint("rrp IS NULL OR rrp >= 0", name="ck_offer_state_rrp"),
        sa.CheckConstraint(
            "quantity IS NULL OR quantity >= 0", name="ck_offer_state_quantity"
        ),
        sa.CheckConstraint(
            "availability IN ('in_stock','out_of_stock','unknown')",
            name="ck_offer_state_availability",
        ),
        sa.CheckConstraint(
            "quantity IS NULL OR "
            "(quantity = 0 AND availability = 'out_of_stock') OR "
            "(quantity > 0 AND availability = 'in_stock')",
            name="ck_offer_state_quantity_availability",
        ),
        sa.Index("ix_offer_states_offer_observed", "offer_id", "observed_at"),
        sa.Index("ix_offer_states_run", "sync_run_id"),
        sa.Index("ix_offer_states_observed", "observed_at"),
    )

    id: Mapped[UUID] = mapped_column(StringUUID, primary_key=True)
    offer_id: Mapped[UUID] = mapped_column(
        StringUUID,
        sa.ForeignKey(f"{TENANT_SCHEMA_ALIAS}.partner_offers.id", ondelete="CASCADE"),
    )
    sync_run_id: Mapped[UUID] = mapped_column(
        StringUUID,
        sa.ForeignKey(
            f"{TENANT_SCHEMA_ALIAS}.price_list_sync_runs.id", ondelete="CASCADE"
        ),
    )
    observed_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True))
    purchase_price: Mapped[Decimal] = mapped_column(sa.Numeric(19, 4))
    rrp: Mapped[Decimal | None] = mapped_column(sa.Numeric(19, 4))
    currency: Mapped[str] = mapped_column(sa.String(3))
    availability: Mapped[str] = mapped_column(sa.String(16))
    quantity: Mapped[int | None] = mapped_column(sa.Integer)
    value_hash: Mapped[str] = mapped_column(sa.String(64))
    change_reason: Mapped[str] = mapped_column(sa.String(32))


class PriceListSyncItemModel(TenantBase):
    __tablename__ = "price_list_sync_items"
    __table_args__ = (
        sa.PrimaryKeyConstraint("sync_run_id", "row_number"),
        sa.UniqueConstraint(
            "sync_run_id", "external_id", name="uq_sync_item_external_id"
        ),
    )

    sync_run_id: Mapped[UUID] = mapped_column(
        StringUUID,
        sa.ForeignKey(
            f"{TENANT_SCHEMA_ALIAS}.price_list_sync_runs.id", ondelete="CASCADE"
        ),
    )
    row_number: Mapped[int] = mapped_column(sa.Integer)
    external_id: Mapped[str | None] = mapped_column(sa.String(255))
    sku: Mapped[str | None] = mapped_column(sa.String(255))
    title: Mapped[str | None] = mapped_column(sa.String(255))
    purchase_price: Mapped[Decimal | None] = mapped_column(sa.Numeric(19, 4))
    rrp: Mapped[Decimal | None] = mapped_column(sa.Numeric(19, 4))
    currency: Mapped[str | None] = mapped_column(sa.String(3))
    availability: Mapped[str | None] = mapped_column(sa.String(16))
    quantity: Mapped[int | None] = mapped_column(sa.Integer)
    value_hash: Mapped[str | None] = mapped_column(sa.String(64))
    normalized_payload: Mapped[dict[str, Any]] = mapped_column(
        PortableJSON, default=dict, nullable=False
    )
    validation_errors: Mapped[list[str]] = mapped_column(
        PortableJSON, default=list, nullable=False
    )
