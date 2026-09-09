"""allauth MFA secret encryption and relying party branding."""

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from allauth.mfa.adapter import DefaultMFAAdapter


class MFAAdapter(DefaultMFAAdapter):
    """Encrypt allauth secrets at rest with a separate, stable Fernet key."""

    def encrypt(self, text):
        """Encrypt each MFA secret with the separately configured persistent Fernet key."""
        return (
            "fernet:"
            + Fernet(settings.MFA_ENCRYPTION_KEY).encrypt(text.encode()).decode()
        )

    def decrypt(self, encrypted_text):
        """Reject cleartext and secrets encrypted with a different MFA key."""
        if not encrypted_text.startswith("fernet:"):
            raise ImproperlyConfigured(
                "Core MFA data must use its configured encryption key."
            )
        try:
            return (
                Fernet(settings.MFA_ENCRYPTION_KEY)
                .decrypt(encrypted_text.removeprefix("fernet:").encode())
                .decode()
            )
        except (InvalidToken, ValueError):
            raise ImproperlyConfigured(
                "Core MFA data cannot be decrypted with this key."
            ) from None

    def get_public_key_credential_rp_entity(self):
        """Expose CORE branding in the authenticator registration prompt."""
        result = super().get_public_key_credential_rp_entity()
        result["name"] = "dNiko Alpha"
        return result
