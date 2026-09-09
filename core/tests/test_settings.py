"""Check deployment invariants in fresh processes without opening connections."""

import base64
import json
import os
from pathlib import Path
import subprocess
import sys

from django.test import SimpleTestCase

CORE_DIR = Path(__file__).resolve().parents[1]


class ProductionSettingsTests(SimpleTestCase):
    """Exercise production settings without loading the developer's dotenv file."""

    def environment(self, **overrides):
        """Build a fresh isolated environment using only synthetic credentials."""
        return {
            **{
                key: value
                for key, value in os.environ.items()
                if not key.startswith("CORE_")
            },
            "PYTHONPATH": str(CORE_DIR / "src"),
            "CORE_ENV_FILE": "",
            "CORE_SECRET_KEY": "settings-validation-test-secret",
            "CORE_DEBUG": "false",
            "CORE_PUBLIC_ORIGIN": "https://example.com",
            "CORE_MFA_ENCRYPTION_KEY": base64.urlsafe_b64encode(b"x" * 32).decode(),
            "CORE_REDIS_URL": "redis://127.0.0.1:6379/2",
            **overrides,
        }

    def load(self, environment, code="import dnk_core.settings"):
        """Import settings in a subprocess to avoid Django's settings cache."""
        return subprocess.run(
            [sys.executable, "-c", code],
            cwd=CORE_DIR,
            env=environment,
            capture_output=True,
            text=True,
            timeout=10,
        )

    def test_production_requires_https_persistent_encryption_and_shared_rate_limits(
        self,
    ):
        """Reject production configurations that weaken mandatory protections."""
        for name, value, message in (
            ("CORE_PUBLIC_ORIGIN", "http://example.com", "CORE_PUBLIC_ORIGIN"),
            ("CORE_MFA_ENCRYPTION_KEY", "", "CORE_MFA_ENCRYPTION_KEY"),
            ("CORE_REDIS_URL", "", "CORE_REDIS_URL"),
            (
                "CORE_EMAIL_VERIFY_CERTIFICATE",
                "false",
                "CORE_EMAIL_VERIFY_CERTIFICATE",
            ),
        ):
            with self.subTest(setting=name):
                result = self.load(self.environment(**{name: value}))
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(message, result.stderr)

    def test_secure_host_only_session_cookie_csrf_and_database_isolation(self):
        """Retain cookie, origin and database isolation across config projection."""
        code = """import json
import dnk_core.settings as s
print(json.dumps({
    'session_secure': s.SESSION_COOKIE_SECURE,
    'session_httponly': s.SESSION_COOKIE_HTTPONLY,
    'session_domain': s.SESSION_COOKIE_DOMAIN,
    'csrf_secure': s.CSRF_COOKIE_SECURE,
    'csrf_httponly': s.CSRF_COOKIE_HTTPONLY,
    'samesite': s.SESSION_COOKIE_SAMESITE,
    'search_path': s.DATABASES['default']['OPTIONS']['options'],
    'passkey_insecure': s.MFA_WEBAUTHN_ALLOW_INSECURE_ORIGIN,
    'session_engine': s.SESSION_ENGINE,
    'phone_enabled': s.PHONE_LOGIN_ENABLED,
}))
"""
        result = self.load(self.environment(), code)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            json.loads(result.stdout),
            {
                "session_secure": True,
                "session_httponly": True,
                "session_domain": None,
                "csrf_secure": True,
                "csrf_httponly": True,
                "samesite": "Lax",
                "search_path": "-c search_path=core",
                "passkey_insecure": False,
                "session_engine": "django.contrib.sessions.backends.db",
                "phone_enabled": False,
            },
        )
