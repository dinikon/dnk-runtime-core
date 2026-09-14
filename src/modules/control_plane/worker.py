"""Dedicated Runtime RabbitMQ workers and durable outbox/recovery loops.

Run: python -m src.modules.control_plane.worker [--healthcheck]
"""

import argparse
import asyncio
import logging
from datetime import timedelta
from uuid import UUID

from sqlalchemy import or_, select, update

from src.config import dnk_config
from src.config.infrastructure.rabbitmq_config import RabbitMQSettings
from src.modules.control_plane.infrastructure.readiness import (
    auth_store_key,
    auth_store_ready,
    heartbeat_key,
    instance_status,
    observe_zone,
    save_observation,
)
from src.modules.control_plane.infrastructure.services import now
from src.modules.control_plane.infrastructure.worker_engine import (
    AccessDelivery,
    Installer,
    due_attempts,
    retry_delay,
)
from src.modules.control_plane.infrastructure.models import DeliveryModel
from src.modules.shared.application.messaging import (
    BrokerExchange,
    BrokerMessage,
    BrokerQueue,
)
from src.modules.shared.infrastructure.messaging import (
    RabbitMQBrokerProvider,
    RabbitMQBrokerPublisher,
    RabbitMQTopologyManager,
    to_rabbit_exchange,
    to_rabbit_queue,
)
from src.modules.shared.infrastructure.persistence.database_helper import db_helper

log = logging.getLogger(__name__)
EXCHANGE = BrokerExchange(name="dnk.runtime.control-plane", type="direct", durable=True)


class RuntimeWorker:
    def __init__(self, session_factory, settings, schema_prefix, provider=None):
        self.sessions, self.settings = session_factory, settings
        self.provider = provider or RabbitMQBrokerProvider(
            RabbitMQSettings(
                enabled=True,
                url=settings.rabbitmq_url,
                prefetch=1,
                publisher_confirms=True,
            )
        )
        self.publisher = RabbitMQBrokerPublisher(self.provider)
        from src.modules.control_plane.infrastructure.deletion import DeletionWorker

        self.deletions = DeletionWorker(session_factory, settings, schema_prefix)
        from src.modules.control_plane.infrastructure.role_sync import (
            RoleProjectionSync,
        )

        self.roles = RoleProjectionSync(session_factory, settings, schema_prefix)
        self.installer = Installer(session_factory, settings, schema_prefix)
        self.access = AccessDelivery(session_factory, settings)
        self.install_queue = BrokerQueue(
            name=settings.install_queue, durable=True, routing_key="install"
        )
        self.access_queue = BrokerQueue(
            name=settings.access_queue, durable=True, routing_key="access"
        )
        self.stop = asyncio.Event()
        self._register()

    def _register(self):
        @self.provider.broker.subscriber(
            to_rabbit_queue(self.install_queue), to_rabbit_exchange(EXCHANGE)
        )
        async def install_message(payload: dict):
            if set(payload) != {"attempt_id"}:
                return
            try:
                attempt_id = UUID(payload["attempt_id"])
            except (ValueError, TypeError, AttributeError):
                return
            await self.installer.run(attempt_id)

        @self.provider.broker.subscriber(
            to_rabbit_queue(self.access_queue), to_rabbit_exchange(EXCHANGE)
        )
        async def access_message(payload: dict):
            if set(payload) != {"event_id"}:
                return
            try:
                event_id = UUID(payload["event_id"])
            except (ValueError, TypeError, AttributeError):
                return
            await self.access.run(event_id)

    async def publish(self, kind: str, identifier: UUID):
        key = "attempt_id" if kind == "install" else "event_id"
        async with asyncio.timeout(self.settings.request_timeout_seconds):
            await self.publisher.publish(
                exchange=EXCHANGE,
                routing_key=kind,
                message=BrokerMessage(
                    payload={key: str(identifier)}, message_id=str(identifier)
                ),
            )

    async def dispatch(self):
        # Advance publication schedule in a short transaction. A crash before or
        # after broker confirmation just schedules the same durable UUID again.
        async with self.sessions() as session, session.begin():
            stamp = now()
            events = list(
                (
                    await session.scalars(
                        select(DeliveryModel)
                        .where(
                            or_(
                                DeliveryModel.state == "pending",
                                (DeliveryModel.state == "running")
                                & or_(
                                    DeliveryModel.lease_until.is_(None),
                                    DeliveryModel.lease_until <= stamp,
                                ),
                            ),
                            DeliveryModel.next_attempt_at <= stamp,
                        )
                        .order_by(DeliveryModel.created_at)
                        .limit(100)
                        .with_for_update(skip_locked=True)
                    )
                ).all()
            )
            batch = [(e.event_id, e.kind, e.aggregate_id) for e in events]
            for event in events:
                # Running without a lease means an eligible notification is in
                # flight. Only the consumer assigns a fenced execution lease.
                event.state = "running"
                event.lease_until = None
                event.next_attempt_at = stamp + timedelta(
                    seconds=self.settings.reconcile_interval_seconds
                )
        for event_id, kind, aggregate_id in batch:
            try:
                await self.publish(
                    kind, aggregate_id if kind == "install" else event_id
                )
                if kind == "install":
                    async with self.sessions() as session, session.begin():
                        await session.execute(
                            update(DeliveryModel)
                            .where(DeliveryModel.event_id == event_id)
                            .values(
                                state="delivered", delivered_at=now(), error_code=None
                            )
                        )
            except Exception:
                async with self.sessions() as session, session.begin():
                    event = await session.get(
                        DeliveryModel, event_id, with_for_update=True
                    )
                    if event and event.state == "running" and event.lease_until is None:
                        event.state = "pending"
                        event.attempts += 1
                        event.error_code = "broker_unavailable"
                        event.next_attempt_at = now() + timedelta(
                            seconds=retry_delay(self.settings, event.attempts)
                        )

    async def reconcile(self):
        async with self.sessions() as session:
            attempts = await due_attempts(session)
        for attempt_id in attempts:
            await self.publish("install", attempt_id)

    async def heartbeat(self):
        broker_ready, auth_ready = await asyncio.gather(
            self.provider.broker.ping(
                timeout=min(5, self.settings.request_timeout_seconds)
            ),
            auth_store_ready(
                timeout_seconds=min(5, self.settings.request_timeout_seconds)
            ),
            return_exceptions=True,
        )
        broker_ready, auth_ready = broker_ready is True, auth_ready is True
        healthy = broker_ready and auth_ready
        async with self.sessions() as session, session.begin():
            await save_observation(
                session, auth_store_key(self.settings), auth_ready, auth_ready
            )
            await save_observation(
                session, heartbeat_key(self.settings), healthy, healthy
            )

    async def observations(self):
        async def observe(zone):
            routing, tls = await observe_zone(self.settings, zone)
            async with self.sessions() as session, session.begin():
                await save_observation(session, zone, routing, tls)

        # Zones are independent; a timeout in one never blocks others' observation.
        semaphore = asyncio.Semaphore(8)

        async def limited(zone):
            async with semaphore:
                await observe(zone)

        await asyncio.gather(
            *(limited(zone) for zone in self.settings.allowed_base_domains)
        )

    async def periodic(self, action, interval):
        while not self.stop.is_set():
            try:
                await action()
            except Exception:
                log.warning(
                    "Control Plane background operation failed: %s", action.__name__
                )
            try:
                await asyncio.wait_for(self.stop.wait(), timeout=interval)
            except TimeoutError:
                pass

    async def run(self):
        await self.provider.start()
        topology = RabbitMQTopologyManager(self.provider)
        await topology.declare_exchange(EXCHANGE)
        for queue in (self.install_queue, self.access_queue):
            await topology.bind_queue(
                queue=queue, exchange=EXCHANGE, routing_key=queue.routing_key
            )
        try:
            async with asyncio.TaskGroup() as group:
                for action, interval in (
                    (self.heartbeat, self.settings.heartbeat_interval_seconds),
                    (self.observations, self.settings.observation_interval_seconds),
                    (self.dispatch, self.settings.dispatch_interval_seconds),
                    (self.deletions.due, self.settings.dispatch_interval_seconds),
                    (self.roles.due, self.settings.reconcile_interval_seconds),
                    (self.reconcile, self.settings.reconcile_interval_seconds),
                ):
                    group.create_task(self.periodic(action, interval))
        finally:
            await self.provider.close()


async def main(
    healthcheck: bool = False,
    retry_event: UUID | None = None,
    reconcile_attempt: UUID | None = None,
):
    config = dnk_config.CONTROL_PLANE
    if not config.enabled:
        return 1
    await db_helper.initialize_for_startup()
    try:
        if healthcheck:
            async with db_helper.session_factory() as session:
                return 0 if (await instance_status(session, config)).ready else 1
        if retry_event is not None:
            async with db_helper.session_factory() as session, session.begin():
                event = await session.get(
                    DeliveryModel, retry_event, with_for_update=True
                )
                if event is None or event.state != "blocked":
                    return 1
                event.state, event.error_code, event.lease_until = "pending", None, None
                event.fencing_token += 1
                event.next_attempt_at = now()
            return 0
        if reconcile_attempt is not None:
            await Installer(
                db_helper.session_factory, config, dnk_config.SCHEMA_PREFIX
            ).run(reconcile_attempt)
            return 0
        await RuntimeWorker(
            db_helper.session_factory, config, dnk_config.SCHEMA_PREFIX
        ).run()
        return 0
    finally:
        await db_helper.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Runtime integration worker")
    operations = parser.add_mutually_exclusive_group()
    operations.add_argument("--healthcheck", action="store_true")
    operations.add_argument(
        "--retry-event",
        type=UUID,
        help="Resume one blocked delivery after operator remediation, preserving its payload/version",
    )
    operations.add_argument(
        "--reconcile-attempt",
        type=UUID,
        help="Recheck the same saved installation attempt without creating a new identity",
    )
    arguments = parser.parse_args()
    try:
        raise SystemExit(
            asyncio.run(
                main(
                    arguments.healthcheck,
                    arguments.retry_event,
                    arguments.reconcile_attempt,
                )
            )
        )
    except KeyboardInterrupt:
        pass
