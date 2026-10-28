from dataclasses import dataclass

from src.modules.channels.application.channel.port.jobs import VerificationJob


@dataclass(frozen=True, slots=True)
class PrepareVerificationCommand:
    """Передаёт проверенный envelope задания и текущую lease."""

    job: VerificationJob
    lock_token: str
