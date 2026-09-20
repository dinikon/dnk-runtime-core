from __future__ import annotations

import asyncio
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

from src.modules.shared.infrastructure.jobs.worker import ScheduledJobWorker


class ScheduledJobWorkerTests(unittest.IsolatedAsyncioTestCase):
    def make_worker(self, heartbeat_path: Path) -> ScheduledJobWorker:
        return ScheduledJobWorker(
            session_factory=Mock(),
            dispatcher=Mock(),
            process_limit=100,
            recover_limit=100,
            lock_ttl_seconds=300,
            lock_heartbeat_seconds=60,
            retry_base_seconds=30,
            max_attempts=5,
            poll_interval_seconds=0.01,
            recover_interval_seconds=30,
            heartbeat_path=heartbeat_path,
        )

    async def test_heartbeat_advances_before_slow_job_finishes(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "heartbeat"
            worker = self.make_worker(path)
            started = asyncio.Event()
            release = asyncio.Event()
            stop = asyncio.Event()

            async def slow_job():
                started.set()
                await release.wait()
                stop.set()
                return 1

            worker.recover_once = AsyncMock()
            worker.process_once = AsyncMock(side_effect=slow_job)
            task = asyncio.create_task(worker.run(stop))
            try:
                await asyncio.wait_for(started.wait(), timeout=1)
                first = path.read_text()
                async with asyncio.timeout(1):
                    while path.read_text() == first:
                        await asyncio.sleep(0.005)
                self.assertFalse(task.done())
                release.set()
                await asyncio.wait_for(task, timeout=1)
            finally:
                task.cancel()
                await asyncio.gather(task, return_exceptions=True)

    async def test_poll_failure_propagates_and_stops_heartbeat(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "heartbeat"
            worker = self.make_worker(path)
            worker.recover_once = AsyncMock(side_effect=RuntimeError("database"))
            with self.assertRaisesRegex(RuntimeError, "database"):
                await worker.run(asyncio.Event())
            heartbeat = path.read_text()
            await asyncio.sleep(0.03)
            self.assertEqual(path.read_text(), heartbeat)

    async def test_serial_worker_claims_only_one_job_at_a_time(self):
        worker = self.make_worker(Path("unused"))
        session = AsyncMock()
        worker.session_factory.return_value = session
        repository = AsyncMock()
        repository.claim_due_jobs.return_value = []
        with patch(
            "src.modules.shared.infrastructure.jobs.worker.SqlAlchemyScheduledJobRepository",
            return_value=repository,
        ):
            self.assertEqual(await worker.process_once(), 0)
        self.assertEqual(repository.claim_due_jobs.call_args.kwargs["limit"], 1)
        session.__aenter__.return_value.commit.assert_awaited_once()
