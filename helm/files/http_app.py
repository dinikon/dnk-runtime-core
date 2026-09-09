"""Preserve HTTPS session cookies for the published runtime behind direct Ingress.

This ASGI adapter comes from the chart, so existing images need no rebuild and
the cluster's Ingress controller needs no privileged configuration snippets.
"""

import os
from urllib.parse import urlsplit


class SessionCookieFlags:
    def __init__(self, app, cookie_name, secure):
        self.app = app
        self.cookie_name = cookie_name.encode("ascii")
        self.secure = secure

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or not self.secure:
            return await self.app(scope, receive, send)

        async def send_with_flags(message):
            if message["type"] == "http.response.start":
                headers = []
                for name, value in message.get("headers", []):
                    if name.lower() == b"set-cookie":
                        parts = value.split(b";")
                        if parts[0].split(b"=", 1)[0].strip() == self.cookie_name:
                            # Preserve the value, expiry, domain and path, including
                            # logout cookies. Do not alter unrelated Set-Cookie headers.
                            parts = parts[:1] + [
                                part
                                for part in parts[1:]
                                if part.strip().split(b"=", 1)[0].lower()
                                not in {b"secure", b"httponly", b"samesite"}
                            ]
                            value = (
                                b";".join(parts) + b"; Secure; HttpOnly; SameSite=Lax"
                            )
                    headers.append((name, value))
                message = {**message, "headers": headers}
            await send(message)

        await self.app(scope, receive, send_with_flags)


def create_app():
    from src.app import app

    return SessionCookieFlags(
        app,
        cookie_name=os.environ["AUTH__SESSION_COOKIE_NAME"],
        secure=urlsplit(os.environ["DNK_PUBLIC_ORIGIN"]).scheme == "https",
    )
