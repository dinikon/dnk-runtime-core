from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

from src.management.job_healthcheck import fresh
from src.modules.shared.infrastructure.jobs.worker import ScheduledJobWorker


class ScheduledJobWorkerTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / "heartbeat"
        self.repository = AsyncMock()
        self.repository.claim_due_jobs.return_value = []
        self.repository.extend_lock.return_value = True
        self.sessions = Mock(return_value=AsyncMock())
        self.repository_patch = patch(
            "src.modules.shared.infrastructure.jobs.worker.SqlAlchemyScheduledJobRepository",
            return_value=self.repository,
        )
        self.repository_patch.start()
        self.addCleanup(self.repository_patch.stop)

    def worker(self, **kwargs):
        worker = ScheduledJobWorker(
            session_factory=self.sessions,
            dispatcher=Mock(),
            process_limit=100,
            recover_limit=100,
            lock_ttl_seconds=300,
            lock_heartbeat_seconds=0.01,
            retry_base_seconds=30,
            max_attempts=5,
            poll_interval_seconds=0.01,
            recover_interval_seconds=30,
            heartbeat_path=self.path,
            concurrency=kwargs.pop("concurrency", 2),
            job_timeout_seconds=kwargs.pop("job_timeout_seconds", 2),
            shutdown_grace_seconds=kwargs.pop("shutdown_grace_seconds", 0.03),
            **kwargs,
        )
        worker.recover_once = AsyncMock()
        worker._dispatch = AsyncMock()
        return worker

    def job(self):
        return SimpleNamespace(
            id=uuid4(),
            tenant_id=uuid4(),
            job_type="test",
            lock_token="lease",
            attempts=1,
        )

    async def test_free_slot_refills_while_slow_job_runs_and_heartbeats_stay_fresh(
        self,
    ):
        worker = self.worker()
        jobs = [self.job() for _ in range(3)]
        queue = list(jobs)
        active = set()
        peak = 0
        slow_started, third_started, release = (
            asyncio.Event(),
            asyncio.Event(),
            asyncio.Event(),
        )
        stop = asyncio.Event()

        async def claim(limit):
            self.assertLessEqual(limit, worker.concurrency - len(active))
            claimed = queue[:limit]
            del queue[:limit]
            return claimed

        async def dispatch(job):
            nonlocal peak
            active.add(job.id)
            peak = max(peak, len(active))
            try:
                if job is jobs[0]:
                    slow_started.set()
                    await release.wait()
                elif job is jobs[1]:
                    await slow_started.wait()
                else:
                    self.assertIn(jobs[0].id, active)
                    third_started.set()
                    await release.wait()
            finally:
                active.remove(job.id)

        worker._claim_jobs = AsyncMock(side_effect=claim)
        worker._dispatch.side_effect = dispatch
        task = asyncio.create_task(worker.run(stop))
        try:
            await asyncio.wait_for(third_started.wait(), 1)
            initial = self.path.read_text()
            async with asyncio.timeout(1):
                while self.path.read_text() == initial:
                    await asyncio.sleep(0.005)
            self.assertTrue(fresh(worker.readiness_path))
            self.assertLessEqual(peak, 2)
            async with asyncio.timeout(1):
                while self.repository.extend_lock.await_count < 1:
                    await asyncio.sleep(.005)
            self.assertGreaterEqual(self.repository.extend_lock.await_count, 1)
            release.set()
            async with asyncio.timeout(1):
                while self.repository.mark_done.await_count < 3:
                    await asyncio.sleep(0.005)
            stop.set()
            await asyncio.wait_for(task, 1)
            self.assertFalse(self.path.exists())
        finally:
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)

    async def test_claim_batch_never_exceeds_concurrency(self):
        worker = self.worker(concurrency=3)
        self.assertEqual(await worker.process_once(), 0)
        self.assertEqual(self.repository.claim_due_jobs.call_args.kwargs["limit"], 3)

    async def test_job_deadline_cancels_handler_and_retries(self):
        worker = self.worker(job_timeout_seconds=0.03)
        cancelled = asyncio.Event()

        async def handler(job):
            try:
                await asyncio.Event().wait()
            finally:
                cancelled.set()

        worker._dispatch.side_effect = handler
        await worker._process_job(self.job())
        self.assertTrue(cancelled.is_set())
        self.repository.mark_done.assert_not_awaited()
        self.assertIn(
            "TimeoutError", self.repository.mark_failed.call_args.kwargs["error"]
        )
        self.assertIsNotNone(self.repository.mark_failed.call_args.kwargs["retry_at"])

    async def test_lease_loss_cancels_handler_before_completion(self):
        worker = self.worker()
        self.repository.extend_lock.return_value = False
        worker._dispatch.side_effect = lambda job: None

        async def handler(job):
            await asyncio.Event().wait()

        worker._dispatch.side_effect = handler
        await asyncio.wait_for(worker._process_job(self.job()), 1)
        self.repository.mark_done.assert_not_awaited()
        self.repository.mark_failed.assert_awaited_once()

    async def test_database_outage_clears_readiness_but_worker_recovers(self):
        worker = self.worker()
        worker._claim_jobs = AsyncMock(side_effect=OSError("offline"))
        stop = asyncio.Event()
        worker._ready()
        task = asyncio.create_task(worker.run(stop))
        try:
            async with asyncio.timeout(1):
                while worker._claim_jobs.await_count < 2:
                    await asyncio.sleep(0.005)
            self.assertFalse(worker.readiness_path.exists())
            self.assertTrue(fresh(self.path))
            worker._claim_jobs.side_effect = None
            worker._claim_jobs.return_value = []
            async with asyncio.timeout(1):
                while not fresh(worker.readiness_path):
                    await asyncio.sleep(0.005)
            stop.set()
            await asyncio.wait_for(task, 1)
        finally:
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)

    async def test_shutdown_bounds_active_jobs_and_releases_lease(self):
        worker = self.worker()
        job = self.job()
        worker._claim_jobs = AsyncMock(side_effect=[[job], []])
        started = asyncio.Event()
        cancelled = asyncio.Event()

        async def handler(job):
            started.set()
            try:
                await asyncio.Event().wait()
            finally:
                cancelled.set()

        worker._dispatch.side_effect = handler
        stop = asyncio.Event()
        task = asyncio.create_task(worker.run(stop))
        await asyncio.wait_for(started.wait(), 1)
        stop.set()
        await asyncio.wait_for(task, 1)
        self.assertTrue(cancelled.is_set())
        self.repository.mark_done.assert_not_awaited()
        self.repository.mark_failed.assert_awaited_once()
