"""Public feature discovery exposes policy without exposing configuration secrets."""

from django.test import SimpleTestCase, override_settings


class CapabilitiesAPITests(SimpleTestCase):
    """Exercise anonymous feature discovery independently of database availability."""

    @override_settings(
        AUTH_PASSWORD_MODE="passwordless",
        AUTH_SIGNUP_ENABLED=True,
        EMAIL_CODE_LOGIN_ENABLED=True,
        PHONE_LOGIN_ENABLED=False,
        MFA_PASSKEY_LOGIN_ENABLED=True,
        MFA_PASSKEY_SIGNUP_ENABLED=True,
        MFA_PASSKEY_ENROLLMENT_ENABLED=True,
        GOOGLE_LOGIN_ENABLED=False,
        GITHUB_LOGIN_ENABLED=True,
        TELEGRAM_LOGIN_ENABLED=False,
    )
    def test_guest_receives_only_allowed_public_flags_without_database_access(self):
        """The bootstrap response needs neither a user query nor provider secrets."""
        response = self.client.get("/api/capabilities/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "registrationEnabled": True,
                "passwordLoginEnabled": False,
                "emailCodeLoginEnabled": True,
                "phoneCodeLoginEnabled": False,
                "phoneLoginMode": "any_verified",
                "passkeyLoginEnabled": True,
                "passkeySignupEnabled": True,
                "providers": ["github"],
            },
        )
        self.assertIn("no-store", response.headers["Cache-Control"])

    @override_settings(AUTH_SIGNUP_ENABLED=False)
    def test_registration_switch_also_hides_passkey_signup(self):
        """A specific registration method cannot reopen globally closed signup."""
        data = self.client.get("/api/capabilities/").json()
        self.assertFalse(data["registrationEnabled"])
        self.assertFalse(data["passkeySignupEnabled"])

    def test_capabilities_rejects_mutation_methods(self):
        """Feature discovery has no write operation."""
        self.assertEqual(self.client.post("/api/capabilities/").status_code, 405)
