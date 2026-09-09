"""Exercise typed configuration independently of Django and external services."""

import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from django.core.exceptions import ImproperlyConfigured

from dnk_core.config import CoreSettings, load_config
from dnk_core.configuration.allauth import authentication_settings, social_settings
from dnk_core.configuration.django import application_settings, infrastructure_settings


class CoreConfigurationTests(unittest.TestCase):
    """Verify parsing, precedence and supported policy combinations with synthetic data."""

    def setUp(self):
        """Remove inherited CORE values so no test can consume a working credential."""
        clean = {
            key: value
            for key, value in os.environ.items()
            if not key.startswith("CORE_")
        }
        self.environment = patch.dict(os.environ, clean, clear=True)
        self.environment.start()
        self.addCleanup(self.environment.stop)

    def configuration(self, **overrides):
        """Create development settings with dotenv disabled and an isolated test secret."""
        return load_config(
            env_file=None,
            **{"debug": True, "secret_key": "synthetic-config-secret", **overrides},
        )

    def test_passwordless_default_and_compatible_development_defaults(self):
        """Preserve existing deployment defaults while selecting passwordless primary auth."""
        config = self.configuration()
        self.assertEqual(config.auth_password_mode, "passwordless")
        self.assertEqual(config.effective_public_origin, "http://localhost:8000")
        self.assertEqual(config.effective_allowed_hosts, ["localhost"])
        self.assertEqual(
            config.effective_email_backend,
            "django.core.mail.backends.console.EmailBackend",
        )
        self.assertFalse(config.effective_email_use_tls)
        self.assertEqual(config.redis_db, 2)
        self.assertEqual(config.session_cookie_age, 1209600)
        self.assertIsNone(config.session_remember)
        self.assertEqual(
            self.configuration().effective_mfa_encryption_key,
            config.effective_mfa_encryption_key,
        )

    def test_process_values_override_dotenv_and_runtime_variables_are_ignored(self):
        """Load flat CORE aliases without importing settings from the runtime namespace."""
        with tempfile.TemporaryDirectory() as temporary:
            dotenv = Path(temporary) / "core.env"
            dotenv.write_text(
                "CORE_SECRET_KEY=synthetic-dotenv-secret\nCORE_DEBUG=true\n"
                "CORE_PUBLIC_ORIGIN=http://localhost:8080\n"
                "CORE_ALLOWED_HOSTS=localhost, 127.0.0.1\n"
                "CORE_AUTH_PASSWORD_MODE=optional\n"
                "CORE_EMAIL_NOTIFICATIONS=false\n"
                "CORE_DB_PORT=5433\nDB_HOST=runtime-only\n"
                "NUXT_PUBLIC_SITE_URL=http://localhost:8080\n",
                encoding="utf-8",
            )
            with patch.dict(
                os.environ,
                {"CORE_AUTH_PASSWORD_MODE": "required", "CORE_DB_PORT": "5434"},
            ):
                config = load_config(dotenv)
            self.assertEqual(config.auth_password_mode, "required")
            self.assertEqual(config.db_port, 5434)
            self.assertEqual(config.db_host, "127.0.0.1")
            self.assertEqual(config.effective_allowed_hosts, ["localhost", "127.0.0.1"])
            self.assertFalse(config.email_notifications)

    def test_default_dotenv_is_core_local_independent_of_working_directory(self):
        """Resolve the default dotenv absolutely and never search a parent runtime file."""
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            core = root / "core"
            core.mkdir()
            (root / ".env").write_text("CORE_AUTH_PASSWORD_MODE=required\n")
            (core / ".env").write_text(
                "CORE_SECRET_KEY=synthetic-file-secret\nCORE_DEBUG=true\n"
            )
            previous = Path.cwd()
            try:
                os.chdir(root)
                with patch("dnk_core.config.CORE_DIR", core):
                    config = load_config()
                self.assertEqual(config.auth_password_mode, "passwordless")
            finally:
                os.chdir(previous)

    def test_core_env_file_can_select_or_disable_dotenv(self):
        """Honor explicit dotenv selection and the empty-value isolation switch."""
        with tempfile.TemporaryDirectory() as temporary:
            dotenv = Path(temporary) / "chosen.env"
            dotenv.write_text(
                "CORE_SECRET_KEY=synthetic-file-secret\nCORE_DEBUG=true\nCORE_AUTH_PASSWORD_MODE=optional\n"
            )
            with patch.dict(os.environ, {"CORE_ENV_FILE": str(dotenv)}):
                self.assertEqual(load_config().auth_password_mode, "optional")
            with patch.dict(
                os.environ,
                {
                    "CORE_ENV_FILE": "",
                    "CORE_SECRET_KEY": "synthetic-env-secret",
                    "CORE_DEBUG": "true",
                },
            ):
                with patch("dnk_core.config.CORE_DIR", Path(temporary)):
                    self.assertEqual(load_config().auth_password_mode, "passwordless")

    def test_invalid_values_fail_without_exposing_input_or_secrets(self):
        """Return variable names rather than raw Pydantic input dictionaries."""
        values = (
            ("debug", "private-invalid-value", "CORE_DEBUG"),
            ("db_port", "private-invalid-value", "CORE_DB_PORT"),
            ("email_port", 70000, "CORE_EMAIL_PORT"),
            ("telegram_gateway_timeout", 0, "CORE_TELEGRAM_GATEWAY_TIMEOUT"),
            ("email_timeout", float("inf"), "CORE_EMAIL_TIMEOUT"),
            ("trusted_proxy_count", -1, "CORE_TRUSTED_PROXY_COUNT"),
            ("auth_password_mode", "private-invalid-value", "CORE_AUTH_PASSWORD_MODE"),
            (
                "public_origin",
                "http://private-invalid-value:secret@localhost",
                "CORE_PUBLIC_ORIGIN",
            ),
            (
                "redis_url",
                "https://private-invalid-value:secret@redis",
                "CORE_REDIS_URL",
            ),
            ("time_zone", "private-invalid-value", "CORE_TIME_ZONE"),
        )
        for field, value, name in values:
            with self.subTest(field=field):
                with self.assertRaises(ImproperlyConfigured) as caught:
                    self.configuration(**{field: value})
                self.assertIn(name, str(caught.exception))
                self.assertNotIn("private-invalid-value", str(caught.exception))
                self.assertNotIn("synthetic-config-secret", str(caught.exception))
        config = self.configuration(
            db_password="private-database-password",
            redis_url="redis://:private-redis-password@localhost/2",
            email_host_password="private-smtp-password",
        )
        for value in (
            "private-database-password",
            "private-redis-password",
            "private-smtp-password",
        ):
            self.assertNotIn(value, repr(config))

    def test_modes_project_signup_fields_and_preserve_password_reauthentication(self):
        """Derive registration fields without disabling security password management."""
        for mode, passwords in (
            ("required", ["password1*", "password2*"]),
            ("optional", ["password1", "password2"]),
            ("passwordless", []),
        ):
            with self.subTest(mode=mode):
                values = authentication_settings(
                    self.configuration(auth_password_mode=mode)
                )
                self.assertEqual(
                    values["ACCOUNT_SIGNUP_FIELDS"], ["username*", "email*", *passwords]
                )
                self.assertEqual(
                    values["ACCOUNT_LOGIN_METHODS"],
                    {"email"} if mode == "passwordless" else {"email", "username"},
                )
                self.assertNotIn("AUTHENTICATION_BACKENDS", values)

    def test_passwordless_and_optional_require_email_code_recovery(self):
        """Reject ordinary signup policies that could create inaccessible accounts."""
        for mode in ("passwordless", "optional"):
            with (
                self.subTest(mode=mode),
                self.assertRaisesRegex(
                    ImproperlyConfigured, "CORE_AUTH_EMAIL_CODE_ENABLED"
                ),
            ):
                self.configuration(
                    auth_password_mode=mode, auth_email_code_enabled=False
                )
        config = self.configuration(
            auth_password_mode="required", auth_email_code_enabled=False
        )
        self.assertFalse(
            authentication_settings(config)["ACCOUNT_LOGIN_BY_CODE_ENABLED"]
        )

    def test_provider_switches_are_auto_enabled_disabled_or_validated(self):
        """Handle complete, partial and explicitly disabled provider credentials safely."""
        for name in ("google", "github", "telegram_login"):
            switch = (
                f"{name}_enabled"
                if name == "telegram_login"
                else f"{name}_login_enabled"
            )
            credentials = {
                f"{name}_client_id": "synthetic-id",
                f"{name}_client_secret": "synthetic-secret",
            }
            with self.subTest(provider=name):
                self.assertFalse(
                    self.configuration(
                        **{f"{name}_client_id": "synthetic-id"}
                    ).provider_enabled(name)
                )
                self.assertTrue(
                    self.configuration(**credentials).provider_enabled(name)
                )
                self.assertFalse(
                    self.configuration(
                        **credentials, **{switch: False}
                    ).provider_enabled(name)
                )
                with self.assertRaisesRegex(
                    ImproperlyConfigured, f"CORE_{switch.upper()}"
                ):
                    self.configuration(**{switch: True})
        with self.assertRaisesRegex(
            ImproperlyConfigured, "CORE_TELEGRAM_GATEWAY_ENABLED"
        ):
            self.configuration(telegram_gateway_enabled=True)
        self.assertFalse(
            self.configuration(
                telegram_gateway_token="synthetic-token", telegram_gateway_enabled=False
            ).provider_enabled("telegram_gateway")
        )

    def test_signup_and_enrollment_dependencies_keep_existing_login_available(self):
        """Close new signup or enrollment without removing existing factor support."""
        for overrides in (
            {"auth_passkey_login_enabled": False},
            {"mfa_passkey_enrollment_enabled": False},
        ):
            with (
                self.subTest(overrides=overrides),
                self.assertRaisesRegex(
                    ImproperlyConfigured, "CORE_AUTH_PASSKEY_SIGNUP_ENABLED"
                ),
            ):
                self.configuration(**overrides)
        values = authentication_settings(
            self.configuration(
                auth_signup_enabled=False, mfa_passkey_enrollment_enabled=False
            )
        )
        self.assertFalse(values["MFA_PASSKEY_SIGNUP_ENABLED"])
        self.assertTrue(values["MFA_PASSKEY_LOGIN_ENABLED"])
        self.assertNotIn("MFA_SUPPORTED_TYPES", values)

    def test_timeouts_resends_and_session_choices_project_consistently(self):
        """Share Gateway/login TTL while keeping email confirmation and reauth distinct."""
        config = self.configuration(
            auth_code_timeout=120,
            auth_code_max_attempts=2,
            auth_code_resend_enabled=False,
            email_verification_max_resends=0,
            email_reauthentication_timeout=180,
            email_reauthentication_max_attempts=4,
            email_reauthentication_resend_wait_seconds=45,
            email_reauthentication_max_per_hour=7,
            session_remember="auto",
            telegram_gateway_token="synthetic-gateway-token",
        )
        values = authentication_settings(config)
        self.assertEqual(values["ACCOUNT_LOGIN_BY_CODE_TIMEOUT"], 120)
        self.assertEqual(values["ACCOUNT_PHONE_VERIFICATION_TIMEOUT"], 120)
        self.assertEqual(values["ACCOUNT_PHONE_VERIFICATION_MAX_ATTEMPTS"], 2)
        self.assertFalse(values["ACCOUNT_LOGIN_BY_CODE_SUPPORTS_RESEND"])
        self.assertEqual(values["ACCOUNT_EMAIL_VERIFICATION_MAX_RESEND_COUNT"], 0)
        self.assertEqual(values["EMAIL_REAUTHENTICATION_TIMEOUT"], 180)
        self.assertEqual(values["EMAIL_REAUTHENTICATION_MAX_ATTEMPTS"], 4)
        self.assertEqual(
            values["ACCOUNT_RATE_LIMITS"],
            {"core_email_reauthenticate": "1/45s/user,7/h/user"},
        )
        self.assertEqual(values["ACCOUNT_LOGIN_METHODS"], {"email", "phone"})
        self.assertIsNone(application_settings(config)["ACCOUNT_SESSION_REMEMBER"])
        for value, expected in (("true", True), ("false", False), ("", None)):
            self.assertIs(
                self.configuration(session_remember=value).session_remember, expected
            )

    def test_mail_cache_and_provider_projection_preserve_security_contracts(self):
        """Keep TLS modes exclusive, cache prefixes isolated and OIDC verification fixed."""
        with self.assertRaisesRegex(ImproperlyConfigured, "CORE_EMAIL_USE_TLS"):
            self.configuration(email_use_tls=True, email_use_ssl=True)
        config = self.configuration(
            redis_host="redis",
            redis_password="synthetic:@password",
            telegram_login_client_id="synthetic-client",
            telegram_login_client_secret="synthetic-secret",
        )
        values = infrastructure_settings(config, Path("/synthetic/core"))
        self.assertEqual(
            values["REDIS_URL"], "redis://:synthetic%3A%40password@redis:6379/2"
        )
        self.assertEqual(values["CACHES"]["default"]["KEY_PREFIX"], "dnk:core")
        self.assertEqual(
            values["DATABASES"]["default"]["OPTIONS"]["options"], "-c search_path=core"
        )
        provider = social_settings(config)["SOCIALACCOUNT_PROVIDERS"]["openid_connect"][
            "APPS"
        ][0]
        self.assertEqual(provider["settings"]["scope"], ["openid", "profile"])
        self.assertTrue(provider["settings"]["oauth_pkce_enabled"])
        self.assertFalse(provider["settings"]["fetch_userinfo"])

    def test_all_environment_fields_have_descriptions(self):
        """Keep the settings schema useful as the source for environment documentation."""
        self.assertTrue(
            all(field.description for field in CoreSettings.model_fields.values())
        )
