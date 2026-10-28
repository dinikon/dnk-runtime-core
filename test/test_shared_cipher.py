"""Совместимость общего Cipher с прежними форматами и конфигурацией проекта."""

import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from cryptography.fernet import Fernet
from pydantic import ValidationError
from src.config.app_config import DnkConfig
from src.config.infrastructure.encryption_config import EncryptionSettings
from src.modules.shared.application.crypto.error import (
    CipherNotConfigured,
    CiphertextUnreadable,
)
from src.modules.shared.infrastructure.crypto.fernet_cipher import FernetCipher
from src.modules.shared.presentation.crypto.depends import get_cipher

KEY = "MDEyMzQ1Njc4OWFiY2RlZjAxMjM0NTY3ODlhYmNkZWY="
OTHER_KEY = "YWJjZGVmMDEyMzQ1Njc4OWFiY2RlZjAxMjM0NTY3ODk="


class SharedCipherTests(unittest.TestCase):
    """Проверяет существующие шифротексты и безопасные отказы."""

    def test_existing_channels_and_control_plane_tokens_are_readable(self) -> None:
        """Сохраняет оба прежних формата без перешифровки БД."""
        old = Fernet(KEY.encode())
        cipher = FernetCipher(KEY)
        payload = b'{"token":"fixture-secret"}'
        self.assertEqual(cipher.decrypt(old.encrypt(payload)), payload)
        text = "Секрет Unicode 🔑"
        self.assertEqual(
            cipher.decrypt_text(old.encrypt(text.encode()).decode("ascii")), text
        )
        self.assertEqual(old.decrypt(cipher.encrypt(payload)), payload)
        self.assertEqual(old.decrypt(cipher.encrypt_text(text).encode()).decode(), text)
        self.assertNotIn(KEY, repr(cipher))

    def test_missing_wrong_and_corrupt_keys_fail_without_secret_values(self) -> None:
        """Не создаёт временные ключи и не раскрывает данные при ошибках."""
        for action in (
            lambda: FernetCipher(None).require_configured(),
            lambda: FernetCipher(None).encrypt(b"secret"),
            lambda: FernetCipher(None).decrypt(b"token"),
        ):
            with self.assertRaises(CipherNotConfigured):
                action()
        encrypted = FernetCipher(KEY).encrypt(b"private-value")
        for token in (encrypted, b"malformed-token"):
            with self.assertRaises(CiphertextUnreadable) as error:
                FernetCipher(OTHER_KEY).decrypt(token)
            self.assertNotIn("private-value", str(error.exception))
            self.assertNotIn(token.decode(), str(error.exception))
        with self.assertRaises(CiphertextUnreadable):
            FernetCipher(KEY).decrypt_text("invalid-非-ascii")


class EncryptionConfigTests(unittest.TestCase):
    """Проверяет один ключ и совместимость прежних входов конфигурации."""

    def settings(self, **values: object) -> DnkConfig:
        """Изолирует тест от рабочей .env и переменных оператора."""
        with patch.dict(os.environ, {}, clear=True):
            return DnkConfig(_env_file=None, **values)

    def test_key_and_file_are_exclusive_and_hidden(self) -> None:
        """Загружает постоянный ключ из файла и скрывает его в repr/ошибках."""
        with tempfile.TemporaryDirectory() as directory:
            file = Path(directory) / "encryption.key"
            file.write_text(KEY + "\n", encoding="utf-8")
            settings = EncryptionSettings(key_path=str(file))
            self.assertEqual(settings.resolved_key.get_secret_value(), KEY)
            self.assertNotIn(KEY, repr(settings))
            project = self.settings(ENCRYPTION=settings)
            self.assertEqual(project.ENCRYPTION.resolved_key.get_secret_value(), KEY)
            with self.assertRaises(ValidationError):
                EncryptionSettings(key=KEY, key_path=str(file))
            file.write_text("")
            with self.assertRaises(ValidationError):
                EncryptionSettings(key_path=str(file))
        for values in (
            {"key": "invalid-key-do-not-echo"},
            {"key_path": "/missing/project-encryption.key"},
        ):
            with self.assertRaises(ValidationError) as error:
                EncryptionSettings(**values)
            self.assertNotIn("invalid-key-do-not-echo", str(error.exception))

    def test_empty_settings_do_not_generate_a_key(self) -> None:
        """Ненастроенное шифрование остаётся операционным отказом потребителя."""
        self.assertIsNone(self.settings().ENCRYPTION.resolved_key)
        self.assertIsNone(EncryptionSettings(key="").resolved_key)

    def test_legacy_constructor_inputs_resolve_to_one_config(self) -> None:
        """Поддерживает прежние вложенные документы без полей ключа в модулях."""
        for values in (
            {"CHANNELS": {"CREDENTIALS_ENCRYPTION_KEY": KEY}},
            {"CONTROL_PLANE": {"secret_encryption_key": KEY}},
            {
                "ENCRYPTION": {"key": KEY},
                "CHANNELS": {"CREDENTIALS_ENCRYPTION_KEY": KEY},
                "CONTROL_PLANE": {"secret_encryption_key": KEY},
            },
        ):
            project = self.settings(**values)
            self.assertEqual(project.ENCRYPTION.resolved_key.get_secret_value(), KEY)
            self.assertNotIn("CHANNELS", type(project).model_fields)
            self.assertNotIn(
                "secret_encryption_key", type(project.CONTROL_PLANE).model_fields
            )

    def test_legacy_environment_and_conflicting_keys(self) -> None:
        """Сохраняет имена env, отклоняя разные старые ключи без выбора наугад."""
        cases = [
            {"ENCRYPTION__KEY": KEY},
            {"CHANNELS__CREDENTIALS_ENCRYPTION_KEY": KEY},
            {"CONTROL_PLANE__SECRET_ENCRYPTION_KEY": KEY},
            {
                "ENCRYPTION__KEY": KEY,
                "CHANNELS__CREDENTIALS_ENCRYPTION_KEY": KEY,
                "CONTROL_PLANE__SECRET_ENCRYPTION_KEY": KEY,
            },
        ]
        for env in cases:
            with patch.dict(os.environ, env, clear=True):
                project = DnkConfig(_env_file=None)
                self.assertEqual(
                    project.ENCRYPTION.resolved_key.get_secret_value(), KEY
                )
        with patch.dict(
            os.environ,
            {"ENCRYPTION__KEY": KEY, "CHANNELS__CREDENTIALS_ENCRYPTION_KEY": OTHER_KEY},
            clear=True,
        ):
            with self.assertRaises(ValidationError) as error:
                DnkConfig(_env_file=None)
            self.assertNotIn(KEY, str(error.exception))
            self.assertNotIn(OTHER_KEY, str(error.exception))

    def test_legacy_file_env_and_dotenv_precedence(self) -> None:
        """Переносит прежний key_path и сохраняет приоритет env над dotenv."""
        with tempfile.TemporaryDirectory() as directory:
            key_file = Path(directory) / "key"
            key_file.write_text(KEY + "\n")
            with patch.dict(
                os.environ,
                {"CONTROL_PLANE__ENCRYPTION_KEY_PATH": str(key_file)},
                clear=True,
            ):
                self.assertEqual(
                    DnkConfig(
                        _env_file=None
                    ).ENCRYPTION.resolved_key.get_secret_value(),
                    KEY,
                )
            env_file = Path(directory) / ".env"
            env_file.write_text(
                "CHANNELS__CREDENTIALS_ENCRYPTION_KEY=" + OTHER_KEY + "\n"
            )
            with patch.dict(
                os.environ, {"CHANNELS__CREDENTIALS_ENCRYPTION_KEY": KEY}, clear=True
            ):
                self.assertEqual(
                    DnkConfig(
                        _env_file=env_file
                    ).ENCRYPTION.resolved_key.get_secret_value(),
                    KEY,
                )

    def test_shared_provider_uses_only_project_config(self) -> None:
        """Единая фабрика совместима с Cipher всех потребителей."""
        project = self.settings(ENCRYPTION={"key": KEY})
        with patch(
            "src.modules.shared.presentation.crypto.depends.dnk_config", project
        ):
            self.assertEqual(
                get_cipher().decrypt(Fernet(KEY.encode()).encrypt(b"test")), b"test"
            )

    def test_equivalent_key_encodings_do_not_create_a_conflict(self) -> None:
        """Перевод строки в env и обрезанный файл описывают один ключ Fernet."""
        project = self.settings(
            ENCRYPTION={"key": KEY + "\n"},
            CONTROL_PLANE={"secret_encryption_key": KEY},
        )
        cipher = FernetCipher(project.ENCRYPTION.resolved_key.get_secret_value())
        self.assertEqual(
            cipher.decrypt(Fernet(KEY.encode()).encrypt(b"same-key")), b"same-key"
        )

    def test_enabled_control_plane_requires_the_project_key(self) -> None:
        """Сохраняет проверку ключа на уровне полного проектного конфига."""
        control_plane = dict(
            enabled=True,
            public_origin="https://core.example.test",
            management_origin="https://manage.core.example.test",
            management_host="manage.runtime.example.test",
            instance_id="c50b45a1-acdc-4214-8a64-3fd8fbf8b101",
            allowed_base_domains=["tenant.example.test"],
            trusted_proxy_networks=["127.0.0.1/32"],
            allowed_core_fingerprints=["a" * 64],
            client_cert_path="runtime.crt",
            client_key_path="runtime.key",
            ca_bundle_path="ca.crt",
            ingress_probe_address="ingress.example.test:443",
            rabbitmq_url="amqp://runtime:fixture-password@rabbitmq/provisioning",
        )
        with self.assertRaises(ValidationError):
            self.settings(CONTROL_PLANE=control_plane)
        self.assertTrue(
            self.settings(
                CONTROL_PLANE=control_plane, ENCRYPTION={"key": KEY}
            ).CONTROL_PLANE.enabled
        )
