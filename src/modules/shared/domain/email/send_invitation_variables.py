from __future__ import annotations

from typing import TypedDict


class SendInvitationVariables(TypedDict):
    """Variables for a workspace invitation email."""

    invitation_url: str


__all__ = ["SendInvitationVariables"]
