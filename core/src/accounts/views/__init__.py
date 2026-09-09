"""Stable public views imports for Django and allauth configuration."""

from .codes import RequestLoginCodeView, ConfirmLoginCodeView
from .reauthentication import EmailReauthenticationView
from .security import account_overview, revoke_session, EmailView
from .profile import profile
from .phones import (
    phone_numbers,
    verify_phone,
    verify_phone_contact,
    primary_phone,
    delete_phone,
)
from .recovery_codes import RecoveryCodesView
from .passkeys import (
    AddPasskeyView,
    LoginPasskeyView,
    SignupPasskeyView,
    continue_passkey_signup,
    RemovePasskeyView,
)
