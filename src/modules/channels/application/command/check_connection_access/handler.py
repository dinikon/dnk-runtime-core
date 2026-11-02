"""Проверка доступа между двумя короткими транзакциями worker."""

import asyncio

from src.modules.channels.application.command.check_connection_access.command import (
    CheckConnectionAccessCommand,
)
from src.modules.channels.application.command.check_connection_access.dto import (
    CheckConnectionAccessResultDTO,
)
from src.modules.channels.application.error import (
    ChannelInputError,
    VerificationFailure,
)
from src.modules.channels.application.port.platform import PlatformRegistry
from src.modules.channels.domain.error import (
    InvalidChannelStateError,
    InvalidResourceIdentityError,
)
from src.modules.shared.application.crypto.cipher import Cipher
from src.modules.shared.application.crypto.error import (
    CipherNotConfigured,
    CiphertextUnreadable,
)
from src.modules.shared.application.jobs.scheduled_job_deferred import (
    ScheduledJobDeferred,
)


class CheckConnectionAccessHandler:
    """Координирует расшифровку, внешний вызов и политику повторяемых отказов."""

    def __init__(self, *, platforms: PlatformRegistry, cipher: Cipher) -> None:
        """Принимает только порты, не открывая сессии и транзакции."""
        self._platforms = platforms
        self._cipher = cipher

    async def execute(
        self, command: CheckConnectionAccessCommand
    ) -> CheckConnectionAccessResultDTO:
        """Возвращает окончательный результат либо передаёт повторяемый отказ worker."""
        try:
            plaintext = self._cipher.decrypt(command.encrypted_credentials)
            async with asyncio.timeout(30):
                identity = await self._platforms.get(command.platform_kind).verify(
                    command.config, plaintext
                )
            return CheckConnectionAccessResultDTO(identity=identity, error_code=None)
        except CipherNotConfigured:
            raise ScheduledJobDeferred("Channels encryption key unavailable") from None
        except CiphertextUnreadable:
            error_code = "credentials_unreadable"
        except ChannelInputError as error:
            error_code = error.code
        except InvalidResourceIdentityError:
            error_code = "resource_identity_unavailable"
        except InvalidChannelStateError:
            error_code = "stored_channel_invalid"
        except TimeoutError:
            if command.attempt < command.max_attempts:
                raise VerificationFailure("network_timeout", retryable=True) from None
            error_code = "network_timeout"
        except VerificationFailure as error:
            if error.retryable and command.attempt < command.max_attempts:
                raise
            error_code = error.code
        return CheckConnectionAccessResultDTO(identity=None, error_code=error_code)
