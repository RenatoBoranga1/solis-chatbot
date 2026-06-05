import unittest

from fastapi.testclient import TestClient

from app.main import app


class SystemHealthTest(unittest.TestCase):
    def test_health_returns_service_and_environment(self):
        response = TestClient(app).get("/health")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["status"], "ok")
        self.assertIn("service", payload)
        self.assertIn("environment", payload)


if __name__ == "__main__":
    unittest.main()
