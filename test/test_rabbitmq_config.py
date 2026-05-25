from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from src.config.app_config import DnkConfig
from src.config.infrastructure.communication_queue_config import (
    CommunicationQueueSettings,
)
from src.config.infrastructure.event_bus_config import EventBusSettings
from src.config.infrastructure.rabbitmq_config import RabbitMQSettings


class RabbitMQConfigTests(unittest.TestCase):
    def test_settings_groups_do_not_duplicate_rabbitmq_url(self) -> None:
        self.assertIsInstance(RabbitMQSettings(), RabbitMQSettings)
        self.assertFalse(hasattr(EventBusSettings(), "rabbitmq_url"))
        self.assertFalse(hasattr(CommunicationQueueSettings(), "rabbitmq_url"))

    def test_dnk_config_reads_rabbitmq_event_bus_and_communication_env(self) -> None:
        env = {
            "RABBITMQ__ENABLED": "true",
            "RABBITMQ__URL": "amqp://guest:guest@rabbitmq:5672/",
            "RABBITMQ__PUBLISHER_CONFIRMS": "false",
            "RABBITMQ__PREFETCH": "7",
            "EVENT_BUS__EXCHANGE_NAME": "events.example",
            "COMMUNICATION_QUEUE__QUEUE_NAME": "communication.example",
        }

        with patch.dict(os.environ, env, clear=False):
            config = DnkConfig(_env_file=None)

        self.assertTrue(config.RABBITMQ.enabled)
        self.assertEqual(config.RABBITMQ.url, "amqp://guest:guest@rabbitmq:5672/")
        self.assertFalse(config.RABBITMQ.publisher_confirms)
        self.assertEqual(config.RABBITMQ.prefetch, 7)
        self.assertEqual(config.EVENT_BUS.exchange_name, "events.example")
        self.assertEqual(
            config.COMMUNICATION_QUEUE.queue_name,
            "communication.example",
        )


__all__ = ["RabbitMQConfigTests"]
