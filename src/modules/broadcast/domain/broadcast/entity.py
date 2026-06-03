from dataclasses import dataclass
from datetime import datetime
from typing import Self

from modules.broadcast.domain.broadcast.value_object.broadcast_id import BroadcastIdVO
from modules.broadcast.domain.broadcast.value_object.broadcast_status import (
    BroadcastStatus,
)
from modules.shared import EntityIdVO


@dataclass(slots=True)
class BroadcastEntity:
    id: BroadcastIdVO
    created_at: datetime
    updated_at: datetime

    name: str
    description: str

    status: BroadcastStatus

    template_id: EntityIdVO
    template_version_id: EntityIdVO | None

    source_id: EntityIdVO | None
    mapping_config: BroadcastMappingConfigVO | None
    settings: BroadcastSettingsVO

    total_rows: int
    valid_recipients_count: int
    invalid_recipients_count: int
    duplicate_recipients_count: int

    scheduled_at: datetime | None
    started_at: datetime | None
    completed_at: datetime | None
    cancelled_at: datetime | None

    @classmethod
    def create_draft(
        cls,
        *,
        id_: EntityIdVO,
        name: str,
        template_id: EntityIdVO,
        now: datetime,
        settings: BroadcastSettingsVO,
    ) -> Self:
        return cls(
            id=id_,
            name=name,
            template_id=template_id,
            template_version_id=None,
            status=BroadcastStatus.DRAFT,
            source_id=None,
            mapping_config=None,
            settings=settings,
            total_rows=0,
            valid_recipients_count=0,
            invalid_recipients_count=0,
            duplicate_recipients_count=0,
            scheduled_at=None,
            started_at=None,
            completed_at=None,
            cancelled_at=None,
            created_at=now,
            updated_at=now,
        )

    def attach_source(self, *, source_id: EntityIdVO, now: datetime) -> None:
        self._ensure_editable()
        self.source_id = source_id
        self.updated_at = now

    def update_mapping(
        self,
        *,
        mapping_config: BroadcastMappingConfigVO,
        now: datetime,
    ) -> None:
        self._ensure_editable()
        self.mapping_config = mapping_config
        self.updated_at = now

    def start_preparing(self, *, now: datetime) -> None:
        self._ensure_editable()
        self.status = BroadcastStatus.PREPARING
        self.updated_at = now

    def mark_ready(
        self,
        *,
        total_rows: int,
        valid_recipients_count: int,
        invalid_recipients_count: int,
        duplicate_recipients_count: int,
        template_version_id: EntityIdVO | None,
        now: datetime,
    ) -> None:
        self.status = BroadcastStatus.READY
        self.total_rows = total_rows
        self.valid_recipients_count = valid_recipients_count
        self.invalid_recipients_count = invalid_recipients_count
        self.duplicate_recipients_count = duplicate_recipients_count
        self.template_version_id = template_version_id
        self.updated_at = now

    def start(self, *, now: datetime) -> None:
        if self.status != BroadcastStatus.READY:
            raise ValueError("Broadcast must be ready before start.")
        self.status = BroadcastStatus.SCHEDULED
        self.scheduled_at = self.settings.start_at or now
        self.updated_at = now

    def mark_running(self, *, now: datetime) -> None:
        if self.status not in {BroadcastStatus.SCHEDULED, BroadcastStatus.PAUSED}:
            raise ValueError("Broadcast cannot be marked as running.")
        self.status = BroadcastStatus.RUNNING
        self.started_at = self.started_at or now
        self.updated_at = now

    def pause(self, *, now: datetime) -> None:
        if self.status not in {BroadcastStatus.SCHEDULED, BroadcastStatus.RUNNING}:
            raise ValueError("Only scheduled/running broadcast can be paused.")
        self.status = BroadcastStatus.PAUSED
        self.updated_at = now

    def cancel(self, *, now: datetime) -> None:
        if self.status in {BroadcastStatus.COMPLETED, BroadcastStatus.CANCELLED}:
            return
        self.status = BroadcastStatus.CANCELLED
        self.cancelled_at = now
        self.updated_at = now

    def complete(self, *, now: datetime) -> None:
        self.status = BroadcastStatus.COMPLETED
        self.completed_at = now
        self.updated_at = now

    def _ensure_editable(self) -> None:
        if self.status not in {
            BroadcastStatus.DRAFT,
            BroadcastStatus.READY,
            BroadcastStatus.FAILED,
        }:
            raise ValueError("Broadcast is not editable.")
