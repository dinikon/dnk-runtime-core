"""Backward-compatible imports for email reauthentication state helpers."""

from .services.reauthentication import (
    STATE_KEY,
    uses_email_reauthentication,
    recently_authenticated,
    verified_email,
    code_digest,
    new_state,
    get_state,
    check_code,
)
