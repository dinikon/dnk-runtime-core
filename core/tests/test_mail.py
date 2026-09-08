import smtplib
import ssl
from unittest.mock import patch

from django.core.exceptions import ImproperlyConfigured
from django.core.mail import get_connection
from django.test import SimpleTestCase, override_settings


@override_settings(
    EMAIL_BACKEND="accounts.mail.SMTPEmailBackend",
    EMAIL_VERIFY_CERTIFICATE=True,
    EMAIL_USE_TLS=True,
    EMAIL_USE_SSL=False,
    EMAIL_HOST="smtp.example.invalid",
    EMAIL_HOST_USER="fixture",
    EMAIL_HOST_PASSWORD="fixture",
)
class SMTPCompatibilityTests(SimpleTestCase):
    def test_certificate_and_hostname_validation_are_enabled_by_default(self):
        backend = get_connection()
        self.assertTrue(backend.ssl_context.check_hostname)
        self.assertEqual(backend.ssl_context.verify_mode, ssl.CERT_REQUIRED)

    @override_settings(DEBUG=True, EMAIL_VERIFY_CERTIFICATE=False)
    def test_explicit_development_compatibility_disables_certificate_validation(self):
        backend = get_connection()
        self.assertFalse(backend.ssl_context.check_hostname)
        self.assertEqual(backend.ssl_context.verify_mode, ssl.CERT_NONE)

    @override_settings(DEBUG=False, EMAIL_VERIFY_CERTIFICATE=False)
    def test_production_rejects_unverified_certificates(self):
        with self.assertRaisesMessage(ImproperlyConfigured, "CORE_DEBUG=true"):
            get_connection()

    @override_settings(DEBUG=True, EMAIL_VERIFY_CERTIFICATE=False)
    def test_compatibility_rejects_plaintext_smtp(self):
        with self.assertRaisesMessage(ImproperlyConfigured, "requires STARTTLS"):
            get_connection(use_tls=False, use_ssl=False)

    @override_settings(DEBUG=True, EMAIL_VERIFY_CERTIFICATE=False)
    def test_failed_starttls_never_sends_credentials_or_falls_back(self):
        with patch("django.core.mail.backends.smtp.smtplib.SMTP") as smtp:
            client = smtp.return_value
            client.starttls.side_effect = smtplib.SMTPNotSupportedError(
                "STARTTLS unavailable"
            )
            backend = get_connection()
            with self.assertRaises(smtplib.SMTPNotSupportedError):
                backend.open()
            client.login.assert_not_called()
            client.sendmail.assert_not_called()
            client.send_message.assert_not_called()
            backend.close()

    @override_settings(DEBUG=True, EMAIL_VERIFY_CERTIFICATE=False)
    def test_implicit_tls_also_uses_the_selected_context(self):
        with patch("django.core.mail.backends.smtp.smtplib.SMTP_SSL") as smtp:
            backend = get_connection(use_tls=False, use_ssl=True)
            self.assertTrue(backend.open())
            self.assertIs(smtp.call_args.kwargs["context"], backend.ssl_context)
            smtp.return_value.starttls.assert_not_called()
            smtp.return_value.login.assert_called_once_with("fixture", "fixture")
            backend.close()
