from contextlib import AbstractAsyncContextManager
from typing import Protocol
from src.modules.currency.application.resolution_failure.command.record_failure import (
    RecordRateResolutionFailure,
)
from src.modules.currency.domain.resolution_failure.repository import (
    ResolutionFailureRepository,
)
from src.modules.shared.application.events.outbox_repository_protocol import (
    OutboxRepositoryProtocol,
)


class ResolutionFailureRecorder(Protocol):
    """Persist expected resolution failures independently of their consumer."""

    async def __call__(self, command: RecordRateResolutionFailure) -> None: ...


class FailureAuditTransaction(Protocol):
    """Diagnostic and tenant outbox repositories in one audit transaction."""

    failures: ResolutionFailureRepository
    outbox: OutboxRepositoryProtocol


class FailureAuditTransactions(Protocol):
    """Open an audit unit of work independent from the failing caller."""

    def __call__(self) -> AbstractAsyncContextManager[FailureAuditTransaction]: ...


__all__ = [
    "ResolutionFailureRecorder",
    "FailureAuditTransaction",
    "FailureAuditTransactions",
]
