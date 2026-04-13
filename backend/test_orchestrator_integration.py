"""Integration tests for orchestrator and realtime intelligence endpoints."""
import json
import unittest
from unittest.mock import patch

import app as app_module


class OrchestratorIntegrationTests(unittest.TestCase):
    def setUp(self):
        app_module.app.config["TESTING"] = True
        self.client = app_module.app.test_client()

    def test_orchestrator_query_endpoint(self):
        payload = {
            "message": "open world monitor",
            "language": "en",
            "user_id": "test-user",
            "chat_mode": "general",
            "model_override": "ollama:qwen3:8b",
            "fallback_models": ["groq:llama-3.1-8b-instant"],
        }

        with patch.object(
            app_module.orchestrator,
            "handle_query",
            return_value={
                "response": "Opening World Monitor for a live global intelligence view.",
                "route": "agent",
                "action": "open_world_monitor",
                "actions": [{"action": "open_url", "url": "https://www.worldmonitor.app/"}],
                "web_search_sources": [],
                "language": "en",
                "chat_mode": "general",
            },
        ) as mocked:
            resp = self.client.post("/api/orchestrator/query", json=payload)

        self.assertEqual(resp.status_code, 200)
        body = resp.get_json()
        self.assertEqual(body["route"], "agent")
        self.assertEqual(body["action"], "open_world_monitor")
        self.assertEqual(body["actions"][0]["action"], "open_url")
        mocked.assert_called_once()
        _, kwargs = mocked.call_args
        self.assertEqual(kwargs["model_override"], "ollama:qwen3:8b")
        self.assertEqual(kwargs["fallback_models"], ["groq:llama-3.1-8b-instant"])

    def test_chat_stream_includes_actions_and_chunks(self):
        payload = {
            "message": "brief me",
            "language": "en",
            "user_id": "test-user",
            "chat_mode": "general",
        }

        response_payload = {
            "response": "Alpha Bravo Charlie Delta",
            "route": "agent",
            "action": "world_news",
            "actions": [{"action": "open_url", "url": "https://www.worldmonitor.app/"}],
            "web_search_sources": [{"title": "Demo Source"}],
            "language": "en",
            "chat_mode": "general",
        }

        with patch.object(app_module.orchestrator, "handle_query", return_value=response_payload):
            resp = self.client.post("/api/chat_stream", json=payload)

        self.assertEqual(resp.status_code, 200)
        text = resp.get_data(as_text=True)
        self.assertIn('"actions"', text)
        self.assertIn('"sources"', text)
        self.assertIn('"content"', text)

    def test_events_feed_endpoint(self):
        with patch(
            "app.get_live_feed",
            return_value={
                "generated_at": "2026-04-09T00:00:00Z",
                "count": 1,
                "events": [
                    {
                        "event_id": "evt123",
                        "title": "Demo event",
                        "summary": "Summary",
                        "region": "Global",
                        "severity": "low",
                        "source": "Demo",
                        "link": "https://example.com",
                        "published_at": "",
                        "coordinates": {"lat": 0.0, "lon": 0.0},
                    }
                ],
            },
        ):
            resp = self.client.get("/api/events/feed?limit=5")

        self.assertEqual(resp.status_code, 200)
        body = resp.get_json()
        self.assertEqual(body["status"], "success")
        self.assertEqual(body["count"], 1)

    def test_model_update_query_returns_transparent_response(self):
        payload = {
            "message": "When was your last major model update and training cutoff?",
            "language": "en",
            "user_id": "test-user",
            "chat_mode": "general",
        }

        resp = self.client.post("/api/orchestrator/query", json=payload)
        self.assertEqual(resp.status_code, 200)
        body = resp.get_json()
        self.assertEqual(body["action"], "model_update_info")
        self.assertIn("do not have direct visibility", body["response"].lower())

    def test_geo_summary_endpoint(self):
        with patch(
            "app.get_geo_summary",
            return_value={
                "generated_at": "2026-04-09T00:00:00Z",
                "regions": [{"region": "Global", "events": 2, "lat": 0.0, "lon": 0.0}],
            },
        ):
            resp = self.client.get("/api/dashboard/geo?limit=5")

        self.assertEqual(resp.status_code, 200)
        body = resp.get_json()
        self.assertEqual(body["status"], "success")
        self.assertEqual(len(body["regions"]), 1)

    def test_models_catalog_endpoint(self):
        resp = self.client.get("/api/models/catalog")
        self.assertEqual(resp.status_code, 200)
        body = resp.get_json()
        self.assertEqual(body["status"], "success")
        self.assertIn("default_model_key", body)
        self.assertIn("models", body)
        self.assertTrue(isinstance(body["models"], list))


if __name__ == "__main__":
    unittest.main()
