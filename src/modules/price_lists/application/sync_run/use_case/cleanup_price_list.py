from datetime import timedelta
from src.modules.price_lists.application.sync_run.command.cleanup_price_list_command import (
    CleanupPriceListCommand,
)
from src.modules.price_lists.application.sync_run.ports import ImportTransactionFactory
from src.modules.price_lists.application.sync_run.options import ImportOptions
from src.modules.shared.domain.time.clock_port import ClockPort


class CleanupPriceListUseCase:
    """Удаляет staging пакетами и планирует следующее обслуживание."""

    def __init__(
        self,
        transactions: ImportTransactionFactory,
        clock: ClockPort,
        options: ImportOptions,
    ):
        self.transactions = transactions
        self.clock = clock
        self.options = options

    async def __call__(self, command: CleanupPriceListCommand) -> None:
        """Выполняет сценарий через внедрённые доменные порты."""
        now = self.clock.now()
        next_at = (now + timedelta(days=1)).replace(
            hour=3, minute=0, second=0, microsecond=0
        )
        async with self.transactions() as tx:
            await tx.jobs.require_lease(
                command.tenant_id, command.job_id, command.lock_token, fence=True
            )
            await tx.jobs.schedule_cleanup(command.tenant_id, next_at)
        after = None
        while True:
            async with self.transactions() as tx:
                await tx.jobs.require_lease(
                    command.tenant_id, command.job_id, command.lock_token
                )
                runs = await tx.runs.unfinished_batch(command.tenant_id, after)
                if not runs:
                    break
                after = runs[-1].id
                terminal = await tx.jobs.terminal_jobs(
                    command.tenant_id,
                    [
                        run.scheduled_job_id
                        for run in runs
                        if run.scheduled_job_id is not None
                    ],
                )
                for run in runs:
                    if run.scheduled_job_id is None or run.scheduled_job_id in terminal:
                        run.finish(now, error="Scheduled job ended before publication.")
                        await tx.runs.save(command.tenant_id, run)
                await tx.jobs.require_lease(
                    command.tenant_id, command.job_id, command.lock_token, fence=True
                )
        while True:
            async with self.transactions() as tx:
                await tx.jobs.require_lease(
                    command.tenant_id, command.job_id, command.lock_token
                )
                deleted = await tx.staging.cleanup_batch(
                    command.tenant_id,
                    now - timedelta(days=self.options.failed_staging_retention_days),
                )
                await tx.jobs.require_lease(
                    command.tenant_id, command.job_id, command.lock_token, fence=True
                )
            if not deleted:
                return


__all__ = ["CleanupPriceListUseCase"]
