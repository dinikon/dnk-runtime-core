"""Backward-compatible import path for the telegram_oidc integration."""

from .integrations.telegram_oidc import (
    ISSUER,
    JWKS_URL,
    TelegramOAuth2Adapter,
    TelegramProvider,
    login,
    callback,
)
