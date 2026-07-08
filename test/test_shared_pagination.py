from __future__ import annotations

import base64
import json
import unittest
from datetime import UTC, datetime

from src.modules.shared.application.pagination import CursorCodec, InvalidCursorError


class SharedPaginationTests(unittest.TestCase):
    def test_cursor_codec_round_trips_payload(self) -> None:
        payload = {
            "v": 1,
            "sort": "created_at_desc_id_desc",
            "created_at": datetime(2026, 6, 27, 12, 0, tzinfo=UTC),
            "id": "42",
        }

        encoded = CursorCodec.encode(payload)
        decoded = CursorCodec.decode(encoded)

        self.assertNotIn("=", encoded)
        self.assertEqual(decoded["v"], 1)
        self.assertEqual(decoded["sort"], "created_at_desc_id_desc")
        self.assertEqual(decoded["created_at"], "2026-06-27 12:00:00+00:00")
        self.assertEqual(decoded["id"], "42")

    def test_cursor_codec_rejects_invalid_payload(self) -> None:
        with self.assertRaises(InvalidCursorError):
            CursorCodec.decode("not-a-valid-cursor")

    def test_cursor_codec_rejects_non_object_payload(self) -> None:
        raw = json.dumps(["not", "an", "object"]).encode("utf-8")
        encoded = base64.urlsafe_b64encode(raw).decode("utf-8").rstrip("=")

        with self.assertRaises(InvalidCursorError):
            CursorCodec.decode(encoded)


if __name__ == "__main__":
    unittest.main()
