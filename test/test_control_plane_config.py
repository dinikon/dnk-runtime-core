import unittest

from pydantic import ValidationError

from src.config.deploy.control_plane import ControlPlaneSettings


class ControlPlaneConfigTests(unittest.TestCase):
    def test_disabled_is_inert_and_enabled_requires_trust(self):
        self.assertFalse(ControlPlaneSettings().enabled)
        with self.assertRaises(ValidationError):
            ControlPlaneSettings(enabled=True)

    def test_encryption_is_owned_by_project_settings(self):
        self.assertNotIn("secret_encryption_key", ControlPlaneSettings.model_fields)
        self.assertNotIn("encryption_key_path", ControlPlaneSettings.model_fields)

    def test_invalid_trust_and_protocol_settings_are_rejected(self):
        for values in [
            {"public_origin": "http://core.example.test"},
            {"management_origin": "https://core.example.test/path"},
            {"management_host": "*.example.test"},
            {"allowed_base_domains": ["example.test", "example.test"]},
            {"trusted_proxy_networks": ["0.0.0.0/0"]},
            {"allowed_core_fingerprints": ["arbitrary-name"]},
            {"lease_seconds": 120, "step_timeout_seconds": 120},
            {"install_queue": "same", "access_queue": "same"},
            {"request_timeout_seconds": 11},
            {"rabbitmq_url": "amqp://worker:password@rabbitmq/"},
        ]:
            with self.subTest(values=list(values)):
                with self.assertRaises(ValidationError):
                    ControlPlaneSettings(**values)
