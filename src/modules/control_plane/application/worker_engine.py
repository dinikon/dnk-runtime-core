"""Installation orchestration over a durable, transaction-aware worker port."""

import asyncio
from dataclasses import dataclass
from typing import Protocol
from uuid import UUID


class LostLease(Exception):
    pass


@dataclass(frozen=True)
class InstallationClaim:
    attempt_id: UUID
    token: int
    reconciling_failure: bool


class InstallationExecutor(Protocol):
    async def claim(self, attempt_id: UUID) -> InstallationClaim | None: ...
    async def execute(self, claim: InstallationClaim) -> None: ...
    async def record_failure(self, attempt_id: UUID, token: int) -> None: ...


class InstallAttemptUseCase:
    def __init__(self, executor: InstallationExecutor, timeout_seconds: int):
        self.executor, self.timeout_seconds = executor, timeout_seconds

    async def __call__(self, attempt_id: UUID) -> None:
        claim = await self.executor.claim(attempt_id)
        if claim is None:
            return
        try:
            async with asyncio.timeout(self.timeout_seconds):
                await self.executor.execute(claim)
        except LostLease:
            return
        except Exception:
            # Persistent worker implementations classify only inspected resources;
            # exceptions and transport outcomes never prove absence.
            await self.executor.record_failure(claim.attempt_id, claim.token)
