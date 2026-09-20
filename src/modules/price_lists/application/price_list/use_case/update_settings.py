from datetime import timedelta
from src.modules.price_lists.application.price_list.use_case.dependencies import (
    PriceListUseCase,
)
from src.modules.price_lists.application.price_list.dto.action_dto import ActionDTO
from src.modules.price_lists.domain.price_list.entity import PriceList
from src.modules.price_lists.domain.price_list.error import (
    PriceListStateConflict,
    PriceListValidationError,
)
from src.modules.price_lists.domain.price_list.value_object.configuration import (
    TitleVO,
    SourceConfigurationVO,
    MappingConfigurationVO,
    ScheduleVO,
)
from src.modules.price_lists.domain.price_list.value_object.source_url import (
    SourceUrlVO,
    mask_source_url,
)
from src.modules.price_lists.domain.price_list.preset import prom_xml_config
from src.modules.price_lists.application.price_list.command.update_settings_command import (
    UpdateSettingsCommand,
)


class UpdateSettingsUseCase(PriceListUseCase):
    """Выполняет действие update_settings через внедрённые порты."""

    async def __call__(self, command: UpdateSettingsCommand) -> ActionDTO:
        price = await self.repository.get(command.tenant_id, command.price_list_id)
        price.require_editable()
        title = TitleVO(command.title).value
        schedule = ScheduleVO(
            command.cron_expression,
            command.timezone,
            command.new_item_policy,
            command.missing_item_policy,
            command.missing_threshold,
        )
        next_at = self.calendar.next(
            schedule.cron_expression, schedule.timezone, after=self.clock.now()
        )
        candidate = self.preview.candidate(
            price,
            {
                name: getattr(command, name)
                for name in (
                    "source_url",
                    "source_format",
                    "source_preset",
                    "source_config",
                    "mapping_config",
                )
            },
        )
        changed_source = any(
            candidate[name] != getattr(price, name)
            for name in (
                "source_format",
                "source_preset",
                "source_config",
                "mapping_config",
            )
        ) or (
            command.source_url is not None
            and candidate["source_url"] != self.cipher.decrypt(price.source_url_secret)
        )
        if changed_source:
            await self.preview.inspect(candidate, limit=50, validate=True)
        current = await self.repository.get(
            command.tenant_id, command.price_list_id, for_update=True
        )
        current.require_editable()
        if (
            current.schedule_revision != price.schedule_revision
            or current.mapping_version != price.mapping_version
        ):
            raise PriceListStateConflict(
                "Price-list settings changed during validation."
            )
        values = {
            name: candidate[name]
            for name in (
                "source_format",
                "source_preset",
                "source_config",
                "mapping_config",
            )
        }
        values.update(
            {
                name: getattr(schedule, name)
                for name in (
                    "cron_expression",
                    "timezone",
                    "new_item_policy",
                    "missing_item_policy",
                    "missing_threshold",
                )
            }
        )
        values["title"] = title
        if changed_source:
            values["mapping_version"] = current.mapping_version + 1
        if command.source_url is not None:
            values.update(
                source_url_secret=self.cipher.encrypt(candidate["source_url"]),
                source_url_display=mask_source_url(candidate["source_url"]),
            )
        if any(getattr(current, k) != v for k, v in values.items()):
            values.update(
                schedule_revision=current.schedule_revision + 1,
                next_sync_at=None if current.status == "paused" else next_at,
                status="paused" if current.status == "paused" else "ready",
            )
        current.update(values, command.actor_id, self.clock.now())
        await self.repository.save(command.tenant_id, current)
        return ActionDTO(status="saved")


__all__ = ["UpdateSettingsUseCase"]
