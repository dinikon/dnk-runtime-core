"""Protocol validation and acceptance orchestration independent of persistence."""

import hashlib
import json
from typing import Protocol

from src.modules.control_plane.application.contracts import (
    AttemptResponse,
    ProvisioningCommand,
)


class ProvisioningConflict(Exception):
    """Safe contract conflict, containing no submitted credential or payload."""


class AcceptanceRepository(Protocol):
    async def accept(
        self, command: ProvisioningCommand, command_hash: str, replay_json: str
    ) -> AttemptResponse: ...


class AcceptProvisioningCommand:
    def __init__(self, repository: AcceptanceRepository, settings):
        self.repository, self.settings = repository, settings

    async def __call__(
        self, command: ProvisioningCommand, idempotency_key: str
    ) -> AttemptResponse:
        if idempotency_key != str(command.attempt_id):
            raise ValueError("Idempotency-Key must equal attempt_id")
        command.validate_placement(self.settings)
        canonical = command.model_dump(mode="json")
        canonical["oidc"][
            "client_secret"
        ] = command.oidc.client_secret.get_secret_value()
        serialized = json.dumps(canonical, sort_keys=True, separators=(",", ":"))
        digest = hashlib.sha256(serialized.encode()).hexdigest()
        del canonical["oidc"]["client_secret"]
        replay = json.dumps(canonical, sort_keys=True, separators=(",", ":"))
        return await self.repository.accept(command, digest, replay)
