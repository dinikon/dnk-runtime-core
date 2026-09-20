from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.price_lists.domain.price_list.value_object import PriceListIdVO
from src.modules.price_lists.domain.sync_run.value_object import SyncRunIdVO
from src.modules.price_lists.domain.price_list.value_object.configuration import (
    TitleVO,
    SourceConfigurationVO,
    MappingConfigurationVO,
    ScheduleVO,
)
from src.modules.price_lists.domain.price_list.error import PriceListStateConflict


@dataclass(slots=True)
class PriceList:
    """Настройки, lifecycle и результат последней синхронизации прайса."""

    id: PriceListIdVO
    title: str
    status: str
    source_format: str
    source_preset: str | None
    source_url_secret: str
    source_url_display: str
    source_config: dict[str, Any]
    mapping_config: dict[str, Any]
    mapping_version: int
    cron_expression: str | None
    timezone: str
    new_item_policy: str
    missing_item_policy: str
    missing_threshold: int
    schedule_revision: int
    created_by: EntityIdVO
    updated_by: EntityIdVO
    created_at: datetime
    updated_at: datetime
    next_sync_at: datetime | None = None
    last_sync_run_id: SyncRunIdVO | None = None
    last_success_at: datetime | None = None
    last_error_at: datetime | None = None
    archived_at: datetime | None = None

    @classmethod
    def create(
        cls,
        *,
        price_list_id,
        actor_id,
        title,
        source_format,
        source_preset,
        source_url_secret,
        source_url_display,
        source_config,
        mapping_config,
        now,
    ):
        """Создаёт draft с единым временем и проверенными настройками."""
        SourceConfigurationVO(source_format, source_config)
        return cls(
            price_list_id,
            TitleVO(title).value,
            "draft",
            source_format,
            source_preset,
            source_url_secret,
            source_url_display,
            source_config,
            mapping_config,
            1,
            None,
            "Europe/Kyiv",
            "create",
            "mark_out_of_stock",
            2,
            1,
            actor_id,
            actor_id,
            now,
            now,
        )

    def require_editable(self):
        """Разрешает редактирование только неактивного прайса."""
        if self.status in ("active", "archived"):
            raise PriceListStateConflict(
                "Pause or restore the price list before changing its settings."
            )

    def update(
        self, values: dict[str, Any], actor_id: EntityIdVO, now: datetime
    ) -> bool:
        """Меняет данные и audit только при фактическом изменении."""
        changed = any(getattr(self, key) != value for key, value in values.items())
        if changed:
            for key, value in values.items():
                setattr(self, key, value)
            self.updated_by, self.updated_at = actor_id, now
        return changed

    def configure_mapping(self, source, mapping, actor_id, now):
        """Сохраняет проверенный mapping и переводит draft в ready."""
        self.require_editable()
        SourceConfigurationVO(self.source_format, source)
        MappingConfigurationVO(mapping)
        if (
            self.source_config == source
            and self.mapping_config == mapping
            and self.status in ("ready", "paused")
        ):
            return
        self.update(
            dict(
                source_config=source,
                mapping_config=mapping,
                mapping_version=self.mapping_version + 1,
                status="paused" if self.status == "paused" else "ready",
            ),
            actor_id,
            now,
        )

    def configure_schedule(self, schedule: ScheduleVO, next_at, actor_id, now):
        """Сохраняет расписание и инвалидирует старые occurrences."""
        self.require_editable()
        values = {
            key: getattr(schedule, key)
            for key in (
                "cron_expression",
                "timezone",
                "new_item_policy",
                "missing_item_policy",
                "missing_threshold",
            )
        }
        if all(getattr(self, key) == value for key, value in values.items()):
            return
        self.update(
            values
            | dict(
                schedule_revision=self.schedule_revision + 1,
                next_sync_at=None if self.status == "paused" else next_at,
            ),
            actor_id,
            now,
        )

    def transition(self, action: str, actor_id: EntityIdVO, now: datetime):
        """Применяет бизнес-переход и отзывает старую revision."""
        allowed = {
            "activate": ("ready",),
            "pause": ("active",),
            "resume": ("paused",),
            "archive": ("draft", "ready", "active", "paused", "invalid", "archived"),
            "restore": ("archived",),
        }
        if self.status not in allowed[action]:
            raise PriceListStateConflict("Price-list state does not allow this action.")
        if action == "activate" and (
            not self.mapping_config or not self.cron_expression
        ):
            raise PriceListStateConflict(
                "Mapping and schedule must be configured first."
            )
        if action == "archive" and self.status == "archived":
            return
        status = {
            "activate": "active",
            "resume": "active",
            "pause": "paused",
            "archive": "archived",
            "restore": "paused",
        }[action]
        self.update(
            dict(
                status=status,
                schedule_revision=self.schedule_revision + 1,
                next_sync_at=None,
                archived_at=now if action == "archive" else None,
            ),
            actor_id,
            now,
        )


__all__ = ["PriceList"]
