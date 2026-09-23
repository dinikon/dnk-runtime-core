from __future__ import annotations

from typing import Callable, cast

from src.modules.shared.domain.email import (
    SendInvitationVariables,
    SendOtpCodeVariables,
    SystemEmailKind,
)
from src.modules.shared.infrastructure.email.rendered_email_message import (
    RenderedEmailMessage,
)

_OTP_SUBJECT = "Your sign-in code"
_OTP_BODY_TEMPLATE = (
    "You requested a one-time code to sign in.\n\n"
    "Your code: {otp_code}\n\n"
    "If you did not request this code, you can ignore this email."
)
_INVITATION_SUBJECT = "You're invited to join a workspace"
_INVITATION_BODY_TEMPLATE = (
    "You have been invited to join a workspace.\n\n"
    "Accept the invitation: {invitation_url}\n\n"
    "This invitation link expires in 7 days.\n\n"
    "If you were not expecting this invitation, you can ignore this email."
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


def _render_send_invitation(
    recipient_email: str,
    variables: object,
) -> RenderedEmailMessage:
    payload = cast(SendInvitationVariables, variables)
    return RenderedEmailMessage(
        recipient_email=recipient_email,
        subject=_INVITATION_SUBJECT,
        text_body=_INVITATION_BODY_TEMPLATE.format(
            invitation_url=payload["invitation_url"]
        ),
    )


_RENDERERS: dict[SystemEmailKind, _Renderer] = {
    SystemEmailKind.SEND_INVITATION: _render_send_invitation,
    SystemEmailKind.SEND_OTP_CODE: _render_send_otp_code,
}


__all__ = ["render_system_email"]
