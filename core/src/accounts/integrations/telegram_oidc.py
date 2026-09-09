"""Telegram OIDC keeps allauth's session/state flow and always verifies ID tokens."""

import jwt
import requests

from allauth.account.internal.decorators import login_not_required
from allauth.socialaccount.helpers import render_authentication_error
from allauth.socialaccount.internal import jwtkit
from allauth.socialaccount.providers.oauth2.client import OAuth2Error
from allauth.socialaccount.providers.oauth2.views import (
    OAuth2CallbackView,
    OAuth2LoginView,
)
from allauth.socialaccount.providers.openid_connect.provider import (
    OpenIDConnectProvider,
)
from allauth.socialaccount.providers.openid_connect.views import (
    OpenIDConnectOAuth2Adapter,
)

ISSUER = "https://oauth.telegram.org"
JWKS_URL = ISSUER + "/.well-known/jwks.json"


class TelegramOAuth2Adapter(OpenIDConnectOAuth2Adapter):
    """Validate Telegram identity tokens with pinned issuer and signed RS256 keys."""

    def get_access_token_data(self, request, app, client, pkce_code_verifier=None):
        """Exchange the authorization code with the client ID and PKCE verifier."""
        data = client.get_access_token(
            request.GET.get("code"),
            pkce_code_verifier=pkce_code_verifier,
            extra_data={"client_id": app.client_id},
        )
        self.did_fetch_access_token = True
        return data

    def complete_login(self, request, app, token, **kwargs):
        """Require an ID token before allowing native OIDC account processing."""
        if not kwargs.get("response", {}).get("id_token"):
            raise OAuth2Error("Missing Telegram ID token")
        return super().complete_login(request, app, token, **kwargs)

    def _decode_id_token(self, app, id_token):
        """Verify required claims, signature, issuer and audience using Telegram JWKS."""
        try:
            header = jwt.get_unverified_header(id_token)
            if header.get("alg") != "RS256" or not header.get("kid"):
                raise OAuth2Error("Invalid Telegram signing algorithm or key ID")
            data = jwtkit.verify_and_decode(
                credential=id_token,
                keys_url=JWKS_URL,
                issuer=ISSUER,
                audience=app.client_id,
                lookup_kid=jwtkit.lookup_kid_jwk,
                verify_signature=True,
            )
            if any(claim not in data for claim in ("iss", "aud", "exp", "iat", "sub")):
                raise OAuth2Error("Missing Telegram ID token claims")
            if not isinstance(data["sub"], str) or not data["sub"].strip():
                raise OAuth2Error("Invalid Telegram subject")
            return data
        except (jwt.PyJWTError, KeyError, TypeError, ValueError) as exc:
            raise OAuth2Error("Invalid Telegram ID token") from exc


class TelegramProvider(OpenIDConnectProvider):
    """Expose the restricted Telegram profile scope through native allauth OIDC."""

    oauth2_adapter_class = TelegramOAuth2Adapter
    supports_token_authentication = False

    def get_scope_from_request(self, request):
        # Do not allow query-string scope overrides to request phone or bot access.
        """Keep the fixed openid/profile scope regardless of query overrides."""
        return ["openid", "profile"]

    def get_auth_params_from_request(self, request, action):
        """Reject query-based authorization overrides and extra permissions."""
        return {}

    def extract_email_addresses(self, data):
        """Require a separate locally verified email instead of provider email claims."""
        return []

    def extract_common_fields(self, data):
        """Remove provider email claims before CORE signup processes user details."""
        fields = super().extract_common_fields(data)
        fields.pop("email", None)
        return fields


def _dispatch(request, view_class):
    """Render retryable provider failures without bypassing native OIDC state checks."""
    adapter = TelegramOAuth2Adapter(request, "telegram")
    try:
        return view_class.adapter_view(adapter)(request)
    except (OAuth2Error, requests.RequestException, KeyError, ValueError) as exc:
        # Discovery/token failures should show a retry screen, never a traceback.
        return render_authentication_error(
            request, adapter.get_provider(), exception=exc
        )


@login_not_required
def login(request):
    """Start Telegram authorization through the native CSRF-protected POST flow."""
    return _dispatch(request, OAuth2LoginView)


@login_not_required
def callback(request):
    """Complete Telegram authorization using native one-time session-bound state."""
    return _dispatch(request, OAuth2CallbackView)
