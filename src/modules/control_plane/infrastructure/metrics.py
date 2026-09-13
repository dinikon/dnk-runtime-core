"""Prometheus observations read from durable state, independent of worker pods."""

from prometheus_client import CollectorRegistry, Gauge, REGISTRY, generate_latest
from sqlalchemy import func, select

from src.modules.control_plane.infrastructure.models import (
    DeliveryModel,
    ProvisioningAttemptModel,
    ReadinessObservationModel,
)
from src.modules.control_plane.infrastructure.services import aware, now
from src.modules.control_plane.infrastructure.readiness import auth_store_key


async def render_metrics(session, settings) -> bytes:
    registry = CollectorRegistry()
    auth_store = await session.get(ReadinessObservationModel, auth_store_key(settings))
    auth_ready = bool(
        auth_store
        and auth_store.routing_ready
        and (now() - aware(auth_store.observed_at)).total_seconds()
        <= settings.heartbeat_ttl_seconds
    )
    Gauge(
        "dnk_runtime_readiness_failure",
        "Safe readiness failure reasons",
        ["reason"],
        registry=registry,
    ).labels("auth_store_unavailable").set(0 if auth_ready else 1)
    outbox = Gauge(
        "dnk_runtime_outbox_events",
        "Durable delivery events by kind and state",
        ["kind", "state"],
        registry=registry,
    )
    age = Gauge(
        "dnk_runtime_outbox_oldest_seconds",
        "Age of oldest unacknowledged delivery",
        ["kind"],
        registry=registry,
    )
    counts = (
        await session.execute(
            select(DeliveryModel.kind, DeliveryModel.state, func.count()).group_by(
                DeliveryModel.kind, DeliveryModel.state
            )
        )
    ).all()
    by_state = {(kind, state): count for kind, state, count in counts}
    for kind in ("install", "access"):
        for state in ("pending", "running", "delivered", "blocked"):
            outbox.labels(kind, state).set(by_state.get((kind, state), 0))
        oldest = await session.scalar(
            select(func.min(DeliveryModel.created_at)).where(
                DeliveryModel.kind == kind, DeliveryModel.state != "delivered"
            )
        )
        age.labels(kind).set(
            max(0, (now() - aware(oldest)).total_seconds()) if oldest else 0
        )
    attempts = Gauge(
        "dnk_runtime_installation_attempts",
        "Retained installation attempts",
        ["state", "resources_state"],
        registry=registry,
    )
    counts = (
        await session.execute(
            select(
                ProvisioningAttemptModel.state,
                ProvisioningAttemptModel.resources_state,
                func.count(),
            ).group_by(
                ProvisioningAttemptModel.state, ProvisioningAttemptModel.resources_state
            )
        )
    ).all()
    for state, resources, count in counts:
        attempts.labels(state, resources).set(count)
    expired = await session.scalar(
        select(func.count())
        .select_from(ProvisioningAttemptModel)
        .where(
            ProvisioningAttemptModel.state == "running",
            ProvisioningAttemptModel.lease_until <= now(),
        )
    )
    Gauge(
        "dnk_runtime_installation_expired_leases",
        "Installation claims requiring recovery",
        registry=registry,
    ).set(expired or 0)
    duration = Gauge(
        "dnk_runtime_installation_step_seconds_max",
        "Longest last completed worker step among retained attempts",
        ["state"],
        registry=registry,
    )
    for state, maximum in (
        await session.execute(
            select(
                ProvisioningAttemptModel.state,
                func.max(ProvisioningAttemptModel.step_duration_ms),
            ).group_by(ProvisioningAttemptModel.state)
        )
    ).all():
        duration.labels(state).set((maximum or 0) / 1000)
    zone_age = Gauge(
        "dnk_runtime_zone_observation_age_seconds",
        "Seconds since last zone observation; -1 means missing",
        ["base_domain"],
        registry=registry,
    )
    zone_ready = Gauge(
        "dnk_runtime_zone_ready",
        "Fresh observed routing and TLS readiness",
        ["base_domain", "check"],
        registry=registry,
    )
    for zone in settings.allowed_base_domains:
        observation = await session.get(ReadinessObservationModel, zone)
        elapsed = (
            max(0, (now() - aware(observation.observed_at)).total_seconds())
            if observation
            else -1
        )
        zone_age.labels(zone).set(elapsed)
        for check in ("routing", "tls"):
            ready = (
                observation is not None
                and elapsed <= settings.observation_ttl_seconds
                and getattr(observation, f"{check}_ready")
            )
            zone_ready.labels(zone, check).set(1 if ready else 0)
    # Shared process counters contain only bounded reasons, never users/hosts/secrets.
    return generate_latest(REGISTRY) + generate_latest(registry)
