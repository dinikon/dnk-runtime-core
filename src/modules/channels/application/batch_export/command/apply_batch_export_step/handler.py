from dataclasses import replace
from datetime import timedelta
from src.modules.channels.application.batch_export.access import BatchExportAccess
from src.modules.channels.application.batch_export.command.apply_batch_export_step.command import (
    ApplyBatchExportStepCommand,
)


class ApplyBatchExportStepHandler:
    """Применяет результат под lease и выдаёт следующий durable intent."""

    def __init__(self, access: BatchExportAccess) -> None:
        """Принимает специализированные порты одной транзакции."""
        self.a = access

    async def execute(self, command: ApplyBatchExportStepCommand) -> None:
        """Не объявляет успех по запуску импорта и не повторяет неоднозначный POST."""
        a = self.a
        run, _ = await a.locked(command.run_id)
        expected = {"submit": "submitting"}.get(command.mode, command.mode)
        if run.sequence != command.sequence or run.status != expected:
            return
        now, delay, changed = a.clock.now(), 0, ()
        if command.error_code is not None:
            if command.mode == "submit":
                run.fail(command.error_code, now, uncertain=command.uncertain)
            elif command.error_code in (
                "permission_denied",
                "invalid_provider_response",
                "invalid_export_snapshot",
                "invalid_xml_character",
                "export_feed_too_large",
            ):
                run.fail(
                    command.error_code,
                    now,
                    uncertain=command.mode in ("processing", "verifying"),
                )
            elif (
                command.mode == "preparing"
                and command.item is not None
                and command.error_code
                in (
                    "publication_not_found",
                    "unsupported_publication_type",
                    "invalid_publication_identity",
                )
            ):
                changed = (
                    command.item.prepared(
                        command.item.desired, None, (command.error_code,)
                    ),
                )
                run.touch(now)
            elif (
                command.mode == "verifying"
                and command.item is not None
                and command.error_code == "publication_not_found"
            ):
                changed = (command.item.verified(("publication_not_found",)),)
                run.touch(now)
            else:
                run.wait(now)
                delay = 60
                if run.status == "unknown" and command.mode not in (
                    "processing",
                    "verifying",
                ):
                    run.fail(command.error_code, now)
        elif (
            command.mode == "preparing"
            and command.item is not None
            and command.inspection is not None
        ):
            result = command.inspection
            changed = (
                command.item.prepared(
                    command.item.desired,
                    result.baseline,
                    result.issues,
                    result.identity_key,
                ),
            )
            run.touch(now)
        elif command.mode == "checking" and command.identities is not None:
            page = command.identities
            targets = await a.runs.matching(
                run.id,
                tuple(v.identity_key for v in page.items if v.identity_key),
                tuple(v.external_id for v in page.items),
            )
            outcomes = []
            for item in targets:
                matches = [v for v in page.items if v.identity_key == item.identity_key]
                updated = item.scanned(
                    len(matches),
                    all(v.external_id == item.external_id for v in matches),
                )
                original = next(
                    (v for v in page.items if v.external_id == item.external_id), None
                )
                if original is not None and original.baseline != item.baseline:
                    updated = updated.exclude("export_source_changed")
                outcomes.append(updated)
            changed = tuple(outcomes)
            run.scanned("complete" if page.complete else page.cursor, now)
        elif (
            command.mode == "building"
            and command.artifact_hash is not None
            and command.artifact_size is not None
        ):
            run.artifact_ready(command.artifact_hash, command.artifact_size, now)
        elif command.mode == "submit" and command.remote_id is not None:
            run.accepted(command.remote_id, now)
            delay = 30
        elif command.mode == "processing" and command.poll is not None:
            if command.poll.finished:
                run.advance("processing", "verifying", now)
                if command.poll.failed:
                    run.note_provider_failure()
            else:
                run.wait(now)
                delay = 30
        elif command.mode == "verifying" and command.item is not None:
            if command.issues == ("export_texts_not_confirmed",) and run.attempts < 10:
                run.wait(now)
                delay = 30
            else:
                changed = (
                    command.item.verified(
                        command.issues,
                        uncertain="export_texts_not_confirmed" in command.issues,
                    ),
                )
                run.finish_item(now)
        else:
            raise ValueError("invalid_batch_export_outcome")
        await a.runs.save(run, changed)
        if run.status in (
            "preparing",
            "checking",
            "building",
            "ready",
            "processing",
            "verifying",
        ):
            await a.jobs.batch_export(
                command.tenant_id, run.id, run.sequence, now + timedelta(seconds=delay)
            )
