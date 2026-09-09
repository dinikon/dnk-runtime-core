"""Local delivery for marked browser fixtures; this module is not in production images."""

import json
from pathlib import Path
from django.conf import settings
from accounts.adapters import AccountAdapter


class BrowserAccountAdapter(AccountAdapter):
    """Exercise real allauth OTP generation without contacting Telegram Gateway."""

    def send_verification_code_sms(self, user, phone, code, **kwargs):
        """Write a code only for the explicitly marked fixture and synthetic numbers."""
        if (
            not settings.DEBUG
            or settings.EMAIL_BACKEND
            != "django.core.mail.backends.filebased.EmailBackend"
        ):
            raise RuntimeError("Browser delivery requires isolated file mail.")
        if user.email != "core_e2e_qa@example.invalid" or phone not in {
            "+12025550123",
            "+12025550124",
            "+12025550125",
        }:
            raise RuntimeError(
                "Refusing phone delivery outside the marked browser fixture."
            )
        directory = Path(settings.EMAIL_FILE_PATH)
        directory.mkdir(parents=True, exist_ok=True)
        (directory / f"phone-{user.pk}.json").write_text(
            json.dumps({"phone": phone, "code": code}), encoding="utf-8"
        )
