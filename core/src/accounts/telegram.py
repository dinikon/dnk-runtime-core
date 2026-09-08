"""Telegram Gateway delivery only; allauth owns code generation and verification."""

import re

import requests
from django.conf import settings


class TelegramDeliveryError(Exception):
    """Delivery failed; never carries the token, phone number, or OTP."""


class TelegramGatewayClient:
    endpoint = "https://gatewayapi.telegram.org/sendVerificationMessage"

    def send_verification_code(self, phone: str, code: str, *, ttl: int = 300) -> str:
        if not settings.PHONE_LOGIN_ENABLED or not settings.TELEGRAM_GATEWAY_TOKEN:
            raise TelegramDeliveryError("provider_unavailable")
        if not re.fullmatch(r"[0-9]{6}", code):
            raise TelegramDeliveryError("invalid_code_format")
        if not re.fullmatch(r"\+[1-9][0-9]{5,14}", phone):
            raise TelegramDeliveryError("invalid_phone_format")
        try:
            response = requests.post(
                self.endpoint,
                headers={"Authorization": f"Bearer {settings.TELEGRAM_GATEWAY_TOKEN}"},
                json={"phone_number": phone, "code": code, "ttl": ttl},
                timeout=settings.TELEGRAM_GATEWAY_TIMEOUT,
                allow_redirects=False,
            )
            response.raise_for_status()
            payload = response.json()
        except (requests.RequestException, ValueError):
            raise TelegramDeliveryError("transport_failure") from None
        if not isinstance(payload, dict) or payload.get("ok") is not True:
            raise TelegramDeliveryError("provider_rejected")
        result = payload.get("result")
        if not isinstance(result, dict) or not isinstance(
            result.get("request_id"), str
        ):
            raise TelegramDeliveryError("invalid_provider_response")
        return result["request_id"]
