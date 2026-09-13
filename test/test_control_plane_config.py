import tempfile
import unittest
from pathlib import Path

from pydantic import ValidationError

from src.config.deploy.control_plane import ControlPlaneSettings

KEY = "MDEyMzQ1Njc4OWFiY2RlZjAxMjM0NTY3ODlhYmNkZWY="


class ControlPlaneConfigTests(unittest.TestCase):
    def test_disabled_is_inert_and_enabled_requires_trust(self):
        self.assertFalse(ControlPlaneSettings().enabled)
        with self.assertRaises(ValidationError):
            ControlPlaneSettings(enabled=True)

    def test_file_key_is_loaded_and_not_disclosed_in_repr(self):
        with tempfile.TemporaryDirectory() as directory:
            key_file = Path(directory) / "key"
            key_file.write_text(KEY + "\n")
            settings = ControlPlaneSettings(encryption_key_path=str(key_file))
            self.assertEqual(settings.secret_encryption_key, KEY)
            self.assertNotIn(KEY, repr(settings))

    def test_invalid_trust_and_protocol_settings_are_rejected(self):
        for values in [
            {"public_origin": "http://core.example.test"},
            {"management_origin": "https://core.example.test/path"},
            {"management_host": "*.example.test"},
            {"allowed_base_domains": ["example.test", "example.test"]},
            {"trusted_proxy_networks": ["0.0.0.0/0"]},
            {"allowed_core_fingerprints": ["arbitrary-name"]},
            {"secret_encryption_key": "weak"},
            {"secret_encryption_key": KEY, "encryption_key_path": "/unused"},
            {"lease_seconds": 120, "step_timeout_seconds": 120},
            {"install_queue": "same", "access_queue": "same"},
            {"request_timeout_seconds": 11},
            {"rabbitmq_url": "amqp://worker:password@rabbitmq/"},
        ]:
            with self.subTest(values=list(values)):
                with self.assertRaises(ValidationError):
                    ControlPlaneSettings(**values)
