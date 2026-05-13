from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

import uuid6

from src.modules.communication.application.outbound_message.processing import (
    OutboundProcessingByIdRepositoryProtocol,
    ProcessingContext,
)
from src.modules.communication.domain.delivery import (
    DeliveryAttempt,
    DeliveryAttemptIdVO,
    DeliveryAttemptServiceProtocol,
)
from src.modules.communication.domain.outbound_message import (
    OutboundMessage,
    OutboundMessageIdVO,
)
from src.modules.communication.domain.provider_connection import (
    ProviderConnectionIdVO,
)
from src.modules.communication.infrastructure.outbound_message import (
    OutboundMessageRuntimeRepository,
)
from src.modules.shared import EntityIdVO


class OutboundProcessingRuntimeRepository(OutboundProcessingByIdRepositoryProtocol):
    """Processing adapter outbound repository и delivery attempt service."""

    def __init__(
        self,
        *,
        outbound_repository: OutboundMessageRuntimeRepository,
        delivery_service: DeliveryAttemptServiceProtocol,
    ) -> None:
        """Инициализирует adapter outbound repository и delivery service."""
        self._outbound_repository = outbound_repository
        self._delivery_service = delivery_service

    async def claim_queued_messages(
        self,
        tenant_id: EntityIdVO,
        limit: int,
    ) -> list[OutboundMessage]:
        """Захватывает queued outbound messages для обработки."""
        return await self._outbound_repository.claim_queued_messages(
            tenant_id,
            limit,
        )

    async def load_processing_context(
        self,
        tenant_id: EntityIdVO,
        outbound_message_id: OutboundMessageIdVO,
    ) -> ProcessingContext:
        """Загружает полный processing context outbound message."""
        return await self._outbound_repository.load_processing_context(
            tenant_id,
            outbound_message_id,
        )

    async def claim_outbound_for_processing(
        self,
        *,
        tenant_id: EntityIdVO,
        outbound_message_id: OutboundMessageIdVO,
        processing_token: EntityIdVO,
        now: datetime,
        lease_until: datetime,
    ) -> OutboundMessage | None:
        """Пытается захватить outbound message по id."""
        return await self._outbound_repository.claim_outbound_for_processing(
            tenant_id=tenant_id,
            outbound_message_id=outbound_message_id,
            processing_token=processing_token,
            now=now,
            lease_until=lease_until,
        )

    async def get_outbound_by_id(
        self,
        tenant_id: EntityIdVO,
        outbound_message_id: OutboundMessageIdVO,
    ) -> OutboundMessage | None:
        """Возвращает outbound message по id."""
        return await self._outbound_repository.get_outbound_by_id(
            tenant_id,
            outbound_message_id,
        )

    async def create_delivery_attempt(
        self,
        *,
        tenant_id: EntityIdVO,
        outbound_message_id: OutboundMessageIdVO,
        provider_connection_id: ProviderConnectionIdVO,
        request_payload: dict[str, Any],
    ) -> DeliveryAttempt:
        """Создает delivery attempt через delivery service."""
        return await self._delivery_service.start_attempt(
            tenant_id=tenant_id,
            delivery_attempt_id=DeliveryAttemptIdVO.from_value(uuid6.uuid7()),
            outbound_message_id=outbound_message_id,
            provider_connection_id=provider_connection_id,
            request_payload=request_payload,
        )

    async def complete_outbound_processing(self, **kwargs: Any) -> bool:
        """Фиксирует outbound success и завершает delivery attempt."""
        applied = await self._outbound_repository.complete_outbound_processing(
            **kwargs,
        )
        if not applied or kwargs.get("delivery_attempt_id") is None:
            return applied
        await self._delivery_service.complete_attempt(
            tenant_id=kwargs["tenant_id"],
            delivery_attempt_id=_delivery_attempt_id(kwargs["delivery_attempt_id"]),
            response_payload=kwargs["response_payload"],
            http_status_code=kwargs["http_status_code"],
            external_message_id=kwargs["external_message_id"],
            finished_at=kwargs["finished_at"],
        )
        return applied

    async def fail_outbound_processing(self, **kwargs: Any) -> bool:
        """Фиксирует outbound failure и завершает delivery attempt."""
        applied = await self._outbound_repository.fail_outbound_processing(**kwargs)
        if not applied or kwargs.get("delivery_attempt_id") is None:
            return applied
        await self._delivery_service.fail_attempt(
            tenant_id=kwargs["tenant_id"],
            delivery_attempt_id=_delivery_attempt_id(kwargs["delivery_attempt_id"]),
            retryable=kwargs.get("retry_at") is not None,
            error_code=kwargs["error_code"],
            error_message=kwargs["error_message"],
            finished_at=kwargs["finished_at"],
            response_payload=kwargs.get("response_payload"),
            http_status_code=kwargs.get("http_status_code"),
            external_message_id=kwargs.get("external_message_id"),
        )
        return applied


def _delivery_attempt_id(value: Any) -> DeliveryAttemptIdVO:
    if type(value) is DeliveryAttemptIdVO:
        return value
    if isinstance(value, UUID):
        return DeliveryAttemptIdVO.from_value(value)
    if hasattr(value, "uuid"):
        return DeliveryAttemptIdVO.from_value(value.uuid)
    return DeliveryAttemptIdVO.from_value(value)


__all__ = ["OutboundProcessingRuntimeRepository"]
