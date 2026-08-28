from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from src.config.app_config import DnkConfig
from src.config.infrastructure.event_bus_config import EventBusSettings
from src.config.infrastructure.rabbitmq_config import RabbitMQSettings


class RabbitMQConfigTests(unittest.TestCase):
    def test_settings_groups_do_not_duplicate_rabbitmq_url(self) -> None:
        self.assertIsInstance(RabbitMQSettings(), RabbitMQSettings)
        self.assertFalse(hasattr(EventBusSettings(), "rabbitmq_url"))

    def test_dnk_config_reads_rabbitmq_and_event_bus_env(self) -> None:
        env = {
            "RABBITMQ__ENABLED": "true",
            "RABBITMQ__URL": "amqp://guest:guest@rabbitmq:5672/",
            "RABBITMQ__PUBLISHER_CONFIRMS": "false",
            "RABBITMQ__PREFETCH": "7",
            "EVENT_BUS__EXCHANGE_NAME": "events.example",
            "EVENT_BUS__PUBLISHER_WORKER_ENABLED": "true",
            "EVENT_BUS__PUBLISHER_IDLE_SLEEP_SECONDS": "0.75",
            "EVENT_BUS__PUBLISHER_ERROR_SLEEP_SECONDS": "3.5",
        }

        with patch.dict(os.environ, env, clear=False):
            config = DnkConfig(_env_file=None)

        self.assertTrue(config.RABBITMQ.enabled)
        self.assertEqual(config.RABBITMQ.url, "amqp://guest:guest@rabbitmq:5672/")
        self.assertFalse(config.RABBITMQ.publisher_confirms)
        self.assertEqual(config.RABBITMQ.prefetch, 7)
        self.assertEqual(config.EVENT_BUS.exchange_name, "events.example")
        self.assertTrue(config.EVENT_BUS.publisher_worker_enabled)
        self.assertEqual(config.EVENT_BUS.publisher_idle_sleep_seconds, 0.75)
        self.assertEqual(config.EVENT_BUS.publisher_error_sleep_seconds, 3.5)
        self.assertFalse(hasattr(config, "COMMUNICATION_QUEUE"))


__all__ = ["RabbitMQConfigTests"]
