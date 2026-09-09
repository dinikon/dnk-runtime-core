"""Secret URL translation is validated independently of runtime application imports."""

import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import unittest
from urllib.parse import urlsplit, unquote

SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "dnk-platform/charts/dnk-runtime-core/files/entrypoint.py"
)
spec = importlib.util.spec_from_file_location("runtime_entrypoint", SCRIPT)
entrypoint = importlib.util.module_from_spec(spec)
spec.loader.exec_module(entrypoint)


class RuntimeEntrypointTest(unittest.TestCase):
    def test_rediss_decodes_credentials_and_database(self):
        env = {
            "DNK_REDIS_URL": "rediss://alice:p%40ss%2F%20word@redis.example:6380/12",
            "REDIS_DB": "1",
        }
        entrypoint.configure_environment(env)
        self.assertEqual(
            env,
            {
                "REDIS_HOST": "redis.example",
                "REDIS_PORT": "6380",
                "REDIS_USERNAME": "alice",
                "REDIS_PASSWORD": "p@ss/ word",
                "REDIS_USE_SSL": "true",
                "REDIS_DB": "12",
            },
        )

    def test_redis_url_defaults_database_and_port(self):
        env = {"DNK_REDIS_URL": "redis://:secret@[::1]"}
        entrypoint.configure_environment(env)
        self.assertEqual(
            (env["REDIS_HOST"], env["REDIS_PORT"], env["REDIS_DB"]),
            ("::1", "6379", "0"),
        )

    def test_rabbit_components_encode_literal_credentials_and_vhost(self):
        password = "a:@/ ?#%'\"$(no-command)"
        env = {
            "RABBITMQ__ENABLED": "true",
            "DNK_RABBITMQ_HOST": "rabbit.example",
            "DNK_RABBITMQ_PORT": "5671",
            "DNK_RABBITMQ_USERNAME": "user:name",
            "DNK_RABBITMQ_PASSWORD": password,
            "DNK_RABBITMQ_VHOST": "tenant / main",
            "DNK_RABBITMQ_USE_SSL": "true",
        }
        entrypoint.configure_environment(env)
        parsed = urlsplit(env["RABBITMQ__URL"])
        self.assertEqual(
            (parsed.scheme, parsed.hostname, parsed.port),
            ("amqps", "rabbit.example", 5671),
        )
        self.assertEqual(unquote(parsed.password), password)
        self.assertEqual(unquote(parsed.username), "user:name")
        self.assertEqual(unquote(parsed.path[1:]), "tenant / main")
        self.assertFalse(any(k.startswith("DNK_RABBITMQ_") for k in env))

    def test_secret_amqps_url_is_preserved(self):
        url = "amqps://user:pass%40word@rabbit.example:5671/%2F"
        env = {"DNK_RABBITMQ_URL": url}
        entrypoint.configure_environment(env)
        self.assertEqual(env, {"RABBITMQ__URL": url})

    def test_disabled_events_do_not_construct_default_url(self):
        env = {"RABBITMQ__ENABLED": "false", "DNK_RABBITMQ_PASSWORD": "not-forwarded"}
        entrypoint.configure_environment(env)
        self.assertNotIn("RABBITMQ__URL", env)
        self.assertNotIn("DNK_RABBITMQ_PASSWORD", env)

    def test_invalid_urls_are_rejected_without_value(self):
        for key, value in [
            ("DNK_REDIS_URL", "https://secret@redis/1"),
            ("DNK_REDIS_URL", "redis://secret@redis:-1/0"),
            ("DNK_REDIS_URL", "redis://secret@redis/tenant"),
            ("DNK_REDIS_URL", "redis://secret@redis/1?ssl=false"),
            ("DNK_RABBITMQ_URL", "amqp://secret@/"),
            ("DNK_RABBITMQ_URL", "amqps://secret@rabbit:99999/"),
        ]:
            with (
                self.subTest(value=value),
                self.assertRaises(entrypoint.ConfigurationError) as error,
            ):
                entrypoint.configure_environment({key: value})
            self.assertNotIn("secret", str(error.exception))

    def test_exec_arguments_never_contain_credentials(self):
        env = os.environ | {
            "DNK_RABBITMQ_URL": "amqp://user:credential-marker@rabbit.example/%2F"
        }
        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                sys.executable,
                "-c",
                "import os,sys; assert 'credential-marker' in os.environ['RABBITMQ__URL']; print(sys.argv)",
            ],
            env=env,
            text=True,
            capture_output=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "['-c']")
        self.assertNotIn("credential-marker", result.stderr)

    def test_startup_error_does_not_print_url(self):
        env = os.environ | {"DNK_REDIS_URL": "redis://secret-marker@redis:99999/"}
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "ignored"],
            env=env,
            text=True,
            capture_output=True,
        )
        self.assertEqual(result.returncode, 1)
        self.assertNotIn("secret-marker", result.stdout + result.stderr)
        self.assertNotIn("Traceback", result.stderr)


if __name__ == "__main__":
    unittest.main()
