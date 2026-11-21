from dataclasses import dataclass

from src.modules.channels.application.port.jobs import VerificationJob
from src.modules.channels.domain.value_object.resource_identity import (
    ResourceIdentityVO,
)


@dataclass(frozen=True, slots=True)
class ApplyVerificationCommand:
    """Передаёт только нормализованный результат внешнего API."""

    job: VerificationJob
    lock_token: str
    identity: ResourceIdentityVO | None
    error_code: str | None
