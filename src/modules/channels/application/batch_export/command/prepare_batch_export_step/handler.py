from dataclasses import replace
from datetime import timedelta
from src.modules.channels.application.batch_export.access import BatchExportAccess
from src.modules.channels.application.batch_export.command.prepare_batch_export_step.command import (
    PrepareBatchExportStepCommand,
)
from src.modules.channels.application.batch_export.command.prepare_batch_export_step.dto import (
    PreparedBatchExportStepDTO,
)
from src.modules.channels.application.plugin_contract import ResourceSettingsDTO
from src.modules.channels.domain.error import ChannelsError


class PrepareBatchExportStepHandler:
    """Допускает ограниченный шаг и фиксирует неопределённость до исходящего POST."""

    def __init__(self, access: BatchExportAccess) -> None:
        """Принимает порты без сетевого клиента и SQL типов."""
        self.a = access

    async def execute(
        self, command: PrepareBatchExportStepCommand
    ) -> PreparedBatchExportStepDTO | None:
        """Завершает локальные переходы или возвращает DTO сетевой работы."""
        a = self.a
        run, channel = await a.locked(command.run_id)
        if run.sequence != command.sequence or run.status not in (
            "preparing",
            "checking",
            "building",
            "ready",
            "submitting",
            "processing",
            "verifying",
        ):
            return None
        now = a.clock.now()
        if now >= run.expires_at:
            run.fail(
                "batch_export_feed_expired",
                now,
                uncertain=run.status in ("submitting", "processing", "verifying"),
            )
            await a.runs.save(run)
            return None
        if run.status == "submitting":
            run.fail("batch_export_submission_unconfirmed", now, uncertain=True)
            await a.runs.save(run)
            return None
        try:
            a.require_capability(channel)
            connection = (
                channel.ensure_network(run.generation)
                if run.status in ("processing", "verifying")
                else channel.ensure_outbound(run.generation)
            )
            if connection.id.uuid != run.connection_id:
                raise ValueError("connection_generation_changed")
        except (ChannelsError, ValueError) as error:
            run.fail(
                str(error), now, uncertain=run.status in ("processing", "verifying")
            )
            await a.runs.save(run)
            return None
        item = None
        mode = run.status
        if run.status == "preparing":
            page = await a.runs.page(run.id, "pending", limit=1)
            if not page:
                counts = await a.runs.counts(run.id)
                run.advance(
                    "preparing", "checking" if counts.get("ready") else "empty", now
                )
                await a.runs.save(run)
                if run.status != "empty":
                    await a.jobs.batch_export(
                        command.tenant_id, run.id, run.sequence, now
                    )
                return None
            item = page[0]
            if item.desired is None:
                try:
                    locales = tuple(connection.settings.options["locales"])
                    snapshots = await a.catalog.snapshot(
                        command.tenant_id, (item.catalog_item_id,), locales
                    )
                    item = replace(item, desired=snapshots.get(item.catalog_item_id))
                    if item.desired is None or item.desired.missing_content():
                        raise ValueError("catalog_content_missing")
                except (ChannelsError, ValueError, KeyError):
                    item = item.prepared(None, None, ("catalog_content_missing",))
                    run.touch(now)
                    await a.runs.save(run, (item,))
                    await a.jobs.batch_export(
                        command.tenant_id, run.id, run.sequence, now
                    )
                    return None
                await a.runs.save(run, (item,))
        if run.status == "checking" and run.identity_cursor == "complete":
            invalid = await a.runs.invalid_identities(run.id)
            if invalid:
                excluded = tuple(
                    target.exclude("export_identity_conflict") for target in invalid
                )
                run.touch(now)
                await a.runs.save(run, excluded)
            else:
                counts = await a.runs.counts(run.id)
                run.advance(
                    "checking", "building" if counts.get("ready") else "empty", now
                )
                await a.runs.save(run)
            if run.status != "empty":
                await a.jobs.batch_export(command.tenant_id, run.id, run.sequence, now)
            return None
        if run.status == "ready":
            if not await a.runs.current(run.id) or not await a.runs.identities_valid(
                run.id
            ):
                run.fail("batch_export_bindings_changed", now)
                await a.runs.save(run)
                return None
            if run.delivery_mode == "file":
                run.complete_file(now)
                await a.runs.save(run)
                return None
            availability = await a.feed_links.availability(command.tenant_id)
            if not availability.delivery_configured:
                run.fail("batch_export_requires_public_host", now)
                await a.runs.save(run)
                return None
            feed_url = await a.feed_links.url(command.tenant_id, run.id, run.expires_at)
            run.claim_submission(now)
            await a.runs.save(run)
            # Recovery наблюдает только неопределённость; никогда не отправляет повторно.
            await a.jobs.batch_export(
                command.tenant_id, run.id, run.sequence, now + timedelta(minutes=2)
            )
            mode = "submit"
        if run.status == "verifying":
            page = await a.runs.page(run.id, "ready", limit=1)
            if not page:
                counts = await a.runs.counts(run.id)
                if counts.get("unknown") or run.remote_id is None:
                    run.fail("batch_export_result_unconfirmed", now, uncertain=True)
                else:
                    succeeded = counts.get("verified", 0)
                    failed = counts.get("failed", 0)
                    target = (
                        "partial"
                        if succeeded and (failed or counts.get("skipped"))
                        else "succeeded" if succeeded else "failed"
                    )
                    run.advance("verifying", target, now)
                await a.runs.save(run)
                return None
            item = page[0]
        return PreparedBatchExportStepDTO(
            run.id,
            run.sequence,
            mode,
            connection.id.uuid,
            channel.platform_kind,
            ResourceSettingsDTO(
                connection.settings.endpoint, connection.settings.options
            ),
            connection.credentials_ciphertext,
            run.expires_at,
            item,
            run.identity_cursor,
            run.remote_id,
            feed_url if mode == "submit" else None,
        )
