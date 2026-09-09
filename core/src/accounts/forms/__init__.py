"""Stable public forms imports for Django and allauth configuration."""

from .authentication import (
    LoginForm,
    SignupForm,
    SocialSignupForm,
    RequestLoginCodeForm,
)
from .profile import ProfileForm
from .phones import AddPhoneForm
from .passkeys import AddPasskeyForm, LoginPasskeyForm, SignupPasskeyForm
from .security import EmailReauthenticationForm, DisconnectForm
