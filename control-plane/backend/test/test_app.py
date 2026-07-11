import unittest

from fastapi.testclient import TestClient

from control_plane.app_factory import create_app


class ControlPlaneAppTests(unittest.TestCase):
    def test_liveness_endpoint(self) -> None:
        with TestClient(create_app()) as client:
            response = client.get("/health/live")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})


if __name__ == "__main__":
    unittest.main()
