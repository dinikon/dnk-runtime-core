"""Exercise the cookie contract when the published backend has no gateway."""

import importlib.util
from pathlib import Path
import unittest

PATH = Path(__file__).resolve().parents[1] / "files/http_app.py"
spec = importlib.util.spec_from_file_location("runtime_http_app", PATH)
http_app = importlib.util.module_from_spec(spec)
spec.loader.exec_module(http_app)


class SessionCookieTests(unittest.IsolatedAsyncioTestCase):
    async def response(self, headers, secure=True, scope_type="http"):
        messages = [
            {"type": "http.response.start", "status": 200, "headers": headers},
            {"type": "http.response.body", "body": b"response"},
        ]
        sent = []

        async def application(scope, receive, send):
            for message in messages:
                await send(message)

        async def send(message):
            sent.append(message)

        await http_app.SessionCookieFlags(application, "dnk_session", secure)(
            {"type": scope_type}, None, send
        )
        self.assertEqual(sent[1], messages[1])
        self.assertEqual(sent[0]["status"], 200)
        return sent[0]["headers"]

    async def test_https_session_preserves_value_expiry_and_other_cookies(self):
        headers = [
            (
                b"set-cookie",
                b"dnk_session=opaque-token; Max-Age=300; Path=/; HttpOnly; SameSite=lax",
            ),
            (b"set-cookie", b"other_session=unchanged; Path=/"),
            (b"content-type", b"application/json"),
        ]
        result = await self.response(headers)
        self.assertEqual(result[1:], headers[1:])
        self.assertEqual(
            result[0][1],
            b"dnk_session=opaque-token; Max-Age=300; Path=/; Secure; HttpOnly; SameSite=Lax",
        )
        self.assertNotIn(b"Secure", headers[0][1])

    async def test_logout_preserves_deletion_and_deduplicates_flags(self):
        result = await self.response(
            [
                (
                    b"Set-Cookie",
                    b'dnk_session=""; expires=Thu, 01 Jan 1970 00:00:00 GMT; Max-Age=0; Path=/; Secure; SameSite=None; HttpOnly',
                )
            ]
        )
        value = result[0][1]
        self.assertIn(b"Max-Age=0", value)
        self.assertIn(b"expires=Thu, 01 Jan 1970 00:00:00 GMT", value)
        self.assertEqual(value.count(b"Secure"), 1)
        self.assertEqual(value.count(b"HttpOnly"), 1)
        self.assertIn(b"SameSite=Lax", value)

    async def test_exact_cookie_name_and_non_cookie_headers(self):
        headers = [
            (b"set-cookie", b"dnk_session_extra=abc"),
            (b"x-cookie", b"dnk_session=abc"),
        ]
        self.assertEqual(await self.response(headers), headers)

    async def test_local_http_and_non_http_scopes_are_unchanged(self):
        headers = [(b"set-cookie", b"dnk_session=abc; SameSite=lax")]
        self.assertEqual(await self.response(headers, secure=False), headers)
        self.assertEqual(await self.response(headers, scope_type="websocket"), headers)
