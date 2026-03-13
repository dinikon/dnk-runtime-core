from __future__ import annotations

import unittest
from unittest.mock import patch

from src.config import dnk_config
from src.modules.identity.application.auth.dto import (
    RequestEmailOtpCommandDTO,
    RequestEmailOtpResultDTO,
)
from src.modules.identity.presentation.api.console_auth import (
    request_email_otp,
)
from src.modules.identity.presentation.api.requests.console_auth import (
    RequestEmailOtpRequestSchema,
)


class FakeRequestEmailOtpUseCase:
    def __init__(self, result: RequestEmailOtpResultDTO):
        self._result = result
        self.last_command: RequestEmailOtpCommandDTO | None = None

    async def execute(
        self,
        dto: RequestEmailOtpCommandDTO,
    ) -> RequestEmailOtpResultDTO:
        self.last_command = dto
        return self._result


class TestConsoleAuthRequestOtpResponse(unittest.IsolatedAsyncioTestCase):
    async def test_request_otp_returns_code_in_dev_mode(self) -> None:
        use_case = FakeRequestEmailOtpUseCase(
            RequestEmailOtpResultDTO(
                token="otp-token",
                expires_in=300,
                code="123456",
            )
        )

        with patch.object(dnk_config, "COMMIT_SHA", "dev"):
            response = await request_email_otp(
                payload=RequestEmailOtpRequestSchema(email="user@example.com"),
                host="acme.local",
                use_case=use_case,
            )

        self.assertEqual(response.token, "otp-token")
        self.assertEqual(response.expires_in, 300)
        self.assertEqual(response.code, "123456")
        self.assertEqual(
            use_case.last_command,
            RequestEmailOtpCommandDTO(
                host="acme.local",
                email="user@example.com",
            ),
        )

    async def test_request_otp_hides_code_outside_dev_mode(self) -> None:
        use_case = FakeRequestEmailOtpUseCase(
            RequestEmailOtpResultDTO(
                token="otp-token",
                expires_in=300,
                code="123456",
            )
        )

        with patch.object(dnk_config, "COMMIT_SHA", "1a2b3c4d"):
            response = await request_email_otp(
                payload=RequestEmailOtpRequestSchema(email="user@example.com"),
                host="acme.local",
                use_case=use_case,
            )

        self.assertEqual(response.token, "otp-token")
        self.assertEqual(response.expires_in, 300)
        self.assertIsNone(response.code)
