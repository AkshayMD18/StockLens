import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app


class FakeGraph:
    def invoke(self, state):
        return {"response": f"Grok: {state['message']}"}


class GroqEndpointTest(unittest.TestCase):
    def test_returns_graph_response(self):
        with patch("app.main.groq_graph", FakeGraph()):
            response = TestClient(app).post("/groq/test", json={"message": "hello"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"response": "Grok: hello"})


if __name__ == "__main__":
    unittest.main()
