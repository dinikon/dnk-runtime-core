from __future__ import annotations

from typing import Callable, cast

from src.modules.shared.infrastructure.email.models import RenderedEmailMessage
from src.modules.shared.kernel.email.models import (
    SendOtpCodeVariables,
    SystemEmailKind,
)

_OTP_SUBJECT = "Your sign-in code"
_OTP_BODY_TEMPLATE = (
    "You requested a one-time code to sign in.\n\n"
    "Your code: {otp_code}\n\n"
    "If you did not request this code, you can ignore this email."
)

_Renderer = Callable[[str, object], RenderedEmailMessage]


def render_system_email(
    kind: SystemEmailKind,
    recipient_email: str,
    variables: object,
) -> RenderedEmailMessage:
    """Собирает rendered email по виду системного письма."""
    return _RENDERERS[kind](recipient_email, variables)


def _render_send_otp_code(
    recipient_email: str,
    variables: object,
) -> RenderedEmailMessage:
    payload = cast(SendOtpCodeVariables, variables)
    return RenderedEmailMessage(
        recipient_email=recipient_email,
        subject=_OTP_SUBJECT,
        text_body=_OTP_BODY_TEMPLATE.format(otp_code=payload["otp_code"]),
    )


_RENDERERS: dict[SystemEmailKind, _Renderer] = {
    SystemEmailKind.SEND_OTP_CODE: _render_send_otp_code,
}


__all__ = ["render_system_email"]
